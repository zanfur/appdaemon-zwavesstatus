# appdaemon-zwavestatus

HomeAssistant has status update issues with some zwave dimmers (notably, the
HomeSeer HS-WD200+), where it will only check once after sending a remote set
command.  The dimmer is almost invariably not yet done ramping to whatever
value it was told do, and dutifully reports whatever dim level it's currently
at.  This invalid state will persist in the HomeAssistant until the next poll
(if enabled) or the next time HomeAssistant does a zwave get, which commonly
is the next set operation.

This app is super simple:  It notices whenever any zwave packet has been sent
or received for a zwave device, and then looks up any light associated with
that zwave device, and sends it a zwave refresh (service zwave.refresh_entity)
while tracking the current state.  This is turn causes a zwave packer has been
sent, triggering the refresh again.  The refreshes stop once the light has
stopped moving for a few refreshes.  There is also a fail-safe to stop if the
refresh count gets too high, to guard against bugs.

There is no delay other than the computation/transport delay of processing the
zwave refresh, so this has the effect of updating the UI about 5x per second,
until the light becomes stable.  When there is no zwave activity at all, this
app does nothing.

Note that this is more useful on switches that support Central Scenes, as any
local button presses will also send a zwave packet, effectively triggering an
instant update.
