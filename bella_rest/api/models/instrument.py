from django.db import models


class Instrument(models.Model):
    InstrumentID           = models.CharField(primary_key=True, max_length=20)        # rb1810
    ExchangeID             = models.CharField(max_length=20)                          # SHFE
    InstrumentName         = models.CharField(max_length=20)                          # 螺纹钢1810
    ExchangeInstID         = models.CharField(max_length=20)                          # rb1810
    ProductID              = models.CharField(max_length=20)                          # rb
    ProductClass           = models.CharField(max_length=20)
    DeliveryYear           = models.IntegerField()                                    # 交割年份
    DeliveryMonth          = models.IntegerField()                                    # 交割月份
    MaxMarketOrderVolume   = models.IntegerField()                                    # 最大市价单手数
    MinMarketOrderVolume   = models.IntegerField()                                    # 最小市价单手数
    MaxLimitOrderVolume    = models.IntegerField()                                    # 最大限价单手数
    MinLimitOrderVolume    = models.IntegerField()                                    # 最小限价单手数
    VolumeMultiple         = models.IntegerField()                                    # 数量乘数（每手多少单位）
    PriceTick              = models.DecimalField(max_digits=20, decimal_places=3)     # 价格变动单位
    CreateDate             = models.CharField(max_length=20)                          # 合约生成日期
    OpenDate               = models.CharField(max_length=20)                          # 开始交易日期
    ExpireDate             = models.CharField(max_length=20)                          # 结束交易日期
    StartDelivDate         = models.CharField(max_length=20)                          # 开始交割日期
    EndDelivDate           = models.CharField(max_length=20)                          # 结束交割日期
    InstLifePhase          = models.CharField(max_length=20)
    IsTrading              = models.IntegerField()
    PositionType           = models.CharField(max_length=20)
    PositionDateType       = models.CharField(max_length=20)
    LongMarginRatio        = models.DecimalField(max_digits=20, decimal_places=3)      # 多头保证金率
    ShortMarginRatio       = models.DecimalField(max_digits=20, decimal_places=3)      # 空头保证金率
    MaxMarginSideAlgorithm = models.CharField(max_length=20)
    UnderlyingInstrID      = models.CharField(max_length=20, blank=True)
    StrikePrice            = models.FloatField()
    OptionsType            = models.CharField(max_length=20)
    UnderlyingMultiple     = models.DecimalField(max_digits=20, decimal_places=3)
    CombinationType        = models.CharField(max_length=20)
