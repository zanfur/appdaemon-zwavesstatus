import appdaemon.plugins.hass.hassapi as hass

#
# ZWave Status
#
# OpenZwave and Homeseer HS-WD200+ dimmers act wonky with regards to updating
# state after a change.  Specifically, it checks too fast, before the device
# state has stopped moving, and then never checks again until the next time a
# command is sent.  This simple plugin watches for any zwave device changes,
# and probes the device until the state of the associated light stops changing.
#
# To opt in to this functionality, the zwave and light entity ids must be the
# same except for the platform name ("zwave" and "light"), and the product
# and manufacturer names must be in the DEVICE_TYPES class variable.  This can
# be made smarter by turning it into an ARG.
#


class ZWaveStatus(hass.Hass):

  # number of times the status has to stay the same before we drop tracking
  COUNT = 2

  # number of polls after which we just give up and drop tracking anyway
  MAX_POLLS = 100

  DELAY = 1

  # types of devices to do tracking for
  DEVICE_TYPES = {
    "HomeSeer Technologies": {"HS-WD200+ Wall Dimmer"}
  }

  def initialize(self):
    self.listen_state(self.zwave_callback, "zwave", attribute="all")
    self.states = {}
    self.counts = {}
    self.tracking = {}
    self.scheduled = set()
    self.device_types = set(
      (m, p) for m, ps in self.DEVICE_TYPES.items() for p in ps
    )
    self.log(
      "initialized: tracking these device types: " +
      ", ".join(f"{m} {p}" for m, p in self.device_types)
    )

  def zwave_callback(self, entity, attribute, old, new, kwargs):
    """callback to check any zwave status updates"""
    # make sure we care about htis device
    manufacturer = old["attributes"]["manufacturer_name"]
    product = old["attributes"]["product_name"]
    if (manufacturer, product) not in self.device_types:
      return

    # look up relevant light info
    light = f"light.{self.split_entity(entity)[1]}"
    new_state = self.state(light)
    old_state = self.states.get(light, {})

    # abort if there isn't a corresponding light
    if not new_state:
      return

    # only log the first and last time
    if not old_state:
      self.tracking[light] = 0
      self.log(f"tracking {light}")

    # track how many times we've matched
    count = self.counts.pop(light, 0)
    if new_state == old_state:
      count += 1
      self.counts[light] = count

    # we've stopped moving/polled long enough, clean up and stop polling
    if count >= self.COUNT or self.tracking[light] > self.MAX_POLLS:
      if count >= self.COUNT:
        self.log(f"{light} now stable after {self.tracking[light]} polls")
      else:
        self.log(f"tracking of {light} aborted after {self.MAX_POLLS} polls")
      self.states.pop(light, None)
      self.counts.pop(light, None)
      self.tracking.pop(light, None)
      return

    # still moving, save the current state and schedule another probe
    if light not in self.scheduled:
      #self.log(f"scheduling refresh for {light}")
      self.states[light] = new_state
      self.tracking[light] += 1
      self.scheduled.add(light)
      self.run_in(self.refresh_callback, self.DELAY, entity_id=light)

  def refresh_callback(self, kwargs):
    entity = kwargs["entity_id"]
    self.scheduled.discard(entity)
    #self.log(f"refresh for {entity}")
    self.call_service("zwave/refresh_entity", entity_id=entity)

  def state(self, entity):
    """gets a dict of all the entity's current state attributes"""
    temp = self.get_state(entity, attribute="all")
    if not temp:
      return None
    state = temp["attributes"]
    state["state"] = temp["state"]
    return state
