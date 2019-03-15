from mongoengine import Document, StringField, BooleanField


class CTPAccount(Document):
    Name     = StringField(min_length=4, max_length=32, primary_key=True)              # 帐号名称
    UserID   = StringField(regex="[0-9]+", min_length=4, max_length=10, required=True) # 登录账号
    Password = StringField(min_length=4, max_length=32, required=True)                 # 密码
    BrokerID = StringField(regex="[0-9]{4}", required=True)                            # 经纪商编号
    MdHost   = StringField(regex="(tcp|udp)://.+:[0-9]+", required=True)               # 行情服务器地址  
    TdHost   = StringField(regex="(tcp|udp)://.+:[0-9]+", required=True)               # 交易服务器地址
    IsReal   = BooleanField(required=True)                                             # 是否实盘账号
