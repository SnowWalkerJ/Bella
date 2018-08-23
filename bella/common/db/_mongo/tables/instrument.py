from mongoengine import Document, StringField, IntField, DecimalField, FloatField


class Instrument(Document):
    InstrumentID           = StringField(required=True, primary_key=True)        # rb1810
    ExchangeID             = StringField(reqiored=True)                          # SHFE
    InstrumentName         = StringField(required=True)                          # 螺纹钢1810
    ExchangeInstID         = StringField(required=True)                          # rb1810
    ProductID              = StringField(required=True)                          # rb
    ProductClass           = StringField(required=True)
    DeliveryYear           = IntField(required=True)                             # 交割年份
    DeliveryMonth          = IntField(required=True, min_value=1, max_value=12)  # 交割月份
    MaxMarketOrderVolume   = IntField()                                          # 最大市价单手数
    MinMarketOrderVolume   = IntField()                                          # 最小市价单手数
    MaxLimitOrderVolume    = IntField()                                          # 最大限价单手数
    MinLimitOrderVolume    = IntField()                                          # 最小限价单手数
    VolumeMultiple         = IntField(required=True)                             # 数量乘数（每手多少单位）
    PriceTick              = DecimalField(required=True)                         # 价格变动单位
    CreateDate             = StringField(regex="[0-9]{8}")                       # 合约生成日期
    OpenDate               = StringField(regex="[0-9]{8}")                       # 开始交易日期
    ExpireDate             = StringField(regex="[0-9]{8}")                       # 结束交易日期
    StartDelivDate         = StringField(regex="[0-9]{8}")                       # 开始交割日期
    EndDelivDate           = StringField(regex="[0-9]{8}")                       # 结束交割日期
    InstLifePhase          = StringField()
    IsTrading              = IntField()
    PositionType           = StringField()
    PositionDateType       = StringField()
    LongMarginRatio        = DecimalField(precision=3)                           # 多头保证金率
    ShortMarginRatio       = DecimalField(precision=3)                           # 空头保证金率
    MaxMarginSideAlgorithm = StringField()
    UnderlyingInstrID      = StringField()
    StrikePrice            = FloatField()
    OptionsType            = StringField()
    UnderlyingMultiple     = DecimalField()
    CombinationType        = StringField()
