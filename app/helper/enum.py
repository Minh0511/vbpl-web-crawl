from enum import Enum


class ObjectNotFoundType(Enum):
    VBPL = 'vbpl'
    ANLE = 'anle'


class VbplTab(Enum):
    FULL_TEXT = 'toanvan'
    FULL_TEXT_HOP_NHAT = 'van-ban-goc-hopnhat'
    FULL_TEXT_HOP_NHAT_2 = 'van-ban-goc-new-hopnhat'
    ATTRIBUTE = 'thuoctinh'
    ATTRIBUTE_HOP_NHAT = 'thuoctinh-hopnhat'
    RELATED_DOC = 'vanbanlienquan'
    DOC_MAP = 'luocdo'
    DOC_MAP_HOP_NHAT = 'luocdo-hopnhat'


class VbplType(Enum):
    PHAP_QUY = 'KetQuaTimKiemVanBan'
    HOP_NHAT = 'KetQuaTimKiemHopNhat'
