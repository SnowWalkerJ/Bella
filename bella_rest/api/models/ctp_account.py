from django.db import models

# Create your models here.


class CTPAccount(models.Model):
    Name     = models.CharField(max_length=32, primary_key=True)          # 帐号名称
    UserID   = models.CharField(max_length=10)                            # 登录账号
    Password = models.CharField(max_length=32)                            # 密码
    BrokerID = models.CharField(max_length=100)                           # 经纪商编号
    MdHost   = models.CharField(max_length=100)                           # 行情服务器地址  
    TdHost   = models.CharField(max_length=100)                           # 交易服务器地址
    IsReal   = models.BooleanField()
