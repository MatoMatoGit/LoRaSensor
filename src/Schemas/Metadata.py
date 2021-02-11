from upyiot.system.Util import DeviceId
from micropython import const

MSG_SECTION_META    = const(1)
MSG_SECTION_DATA    = const(2)
MSG_META_VERSION    = const(10)
MSG_META_TYPE       = const(11)
MSG_META_SUBTYPE    = const(12)
MSG_META_ID         = const(13)

Metadata = {
    MSG_META_VERSION:   1,
    MSG_META_TYPE:      1,
    MSG_META_SUBTYPE:   1,
#    MSG_META_ID:        DeviceId.DeviceId(),
}

MetadataFuncs = {
}