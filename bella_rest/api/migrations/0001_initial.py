# Generated by Django 2.1.7 on 2019-04-13 08:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BarPeriod',
            fields=[
                ('period', models.CharField(max_length=10, primary_key=True, serialize=False)),
            ],
        ),
        migrations.CreateModel(
            name='CTPAccount',
            fields=[
                ('Name', models.CharField(max_length=32, primary_key=True, serialize=False)),
                ('UserID', models.CharField(max_length=10)),
                ('Password', models.CharField(max_length=32)),
                ('BrokerID', models.CharField(max_length=100)),
                ('MdHost', models.CharField(max_length=100)),
                ('TdHost', models.CharField(max_length=100)),
                ('IsReal', models.BooleanField()),
            ],
        ),
        migrations.CreateModel(
            name='CTPOrder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('FrontID', models.CharField(max_length=20)),
                ('SessionID', models.CharField(max_length=20)),
                ('OrderRef', models.CharField(max_length=20)),
                ('InvestorID', models.CharField(max_length=20)),
                ('BrokerID', models.CharField(max_length=20)),
                ('InstrumentID', models.CharField(max_length=20)),
                ('Direction', models.CharField(max_length=1)),
                ('Offset', models.CharField(max_length=1)),
                ('Price', models.DecimalField(decimal_places=2, max_digits=7)),
                ('VolumesTotal', models.IntegerField()),
                ('VolumesTraded', models.IntegerField()),
                ('InsertTime', models.DateTimeField()),
                ('UpdateTime', models.DateTimeField(null=True)),
                ('CancelTime', models.DateTimeField(blank=True, null=True)),
                ('CompleteTime', models.DateTimeField(blank=True, null=True)),
                ('StatusMsg', models.CharField(blank=True, max_length=80, null=True)),
                ('Finished', models.BooleanField(default=False)),
                ('IsDummy', models.BooleanField(default=False)),
                ('Account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.CTPAccount')),
            ],
        ),
        migrations.CreateModel(
            name='CTPTrade',
            fields=[
                ('TradeID', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('Price', models.DecimalField(decimal_places=2, max_digits=7)),
                ('Volume', models.IntegerField()),
                ('TradeTime', models.DateTimeField()),
                ('Account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.CTPAccount')),
                ('CTPOrderID', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.CTPOrder')),
            ],
        ),
        migrations.CreateModel(
            name='Instrument',
            fields=[
                ('InstrumentID', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('ExchangeID', models.CharField(max_length=20)),
                ('InstrumentName', models.CharField(max_length=20)),
                ('ExchangeInstID', models.CharField(max_length=20)),
                ('ProductID', models.CharField(max_length=20)),
                ('ProductClass', models.CharField(max_length=20)),
                ('DeliveryYear', models.IntegerField()),
                ('DeliveryMonth', models.IntegerField()),
                ('MaxMarketOrderVolume', models.IntegerField()),
                ('MinMarketOrderVolume', models.IntegerField()),
                ('MaxLimitOrderVolume', models.IntegerField()),
                ('MinLimitOrderVolume', models.IntegerField()),
                ('VolumeMultiple', models.IntegerField()),
                ('PriceTick', models.DecimalField(decimal_places=3, max_digits=20)),
                ('CreateDate', models.CharField(max_length=20)),
                ('OpenDate', models.CharField(max_length=20)),
                ('ExpireDate', models.CharField(max_length=20)),
                ('StartDelivDate', models.CharField(max_length=20)),
                ('EndDelivDate', models.CharField(max_length=20)),
                ('InstLifePhase', models.CharField(max_length=20)),
                ('IsTrading', models.IntegerField()),
                ('PositionType', models.CharField(max_length=20)),
                ('PositionDateType', models.CharField(max_length=20)),
                ('LongMarginRatio', models.DecimalField(decimal_places=3, max_digits=20)),
                ('ShortMarginRatio', models.DecimalField(decimal_places=3, max_digits=20)),
                ('MaxMarginSideAlgorithm', models.CharField(max_length=20)),
                ('UnderlyingInstrID', models.CharField(max_length=20)),
                ('StrikePrice', models.FloatField()),
                ('OptionsType', models.CharField(max_length=20)),
                ('UnderlyingMultiple', models.DecimalField(decimal_places=3, max_digits=20)),
                ('CombinationType', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('ID', models.AutoField(primary_key=True, serialize=False)),
                ('InstrumentID', models.CharField(max_length=20)),
                ('Direction', models.CharField(max_length=1)),
                ('Offset', models.CharField(max_length=1)),
                ('Price', models.CharField(max_length=8)),
                ('VolumesTotal', models.IntegerField()),
                ('VolumesTraded', models.IntegerField(default=0)),
                ('InsertTime', models.DateTimeField(auto_now_add=True)),
                ('SplitSleepAfterSubmit', models.FloatField()),
                ('SplitSleepAfterCancel', models.FloatField()),
                ('SplitPercent', models.FloatField()),
                ('CancelTime', models.DateTimeField(blank=True, null=True)),
                ('CompleteTime', models.DateTimeField(blank=True, null=True)),
                ('StatusMsg', models.CharField(blank=True, max_length=80)),
                ('Status', models.IntegerField(default=0)),
                ('IsDummy', models.BooleanField(default=False)),
                ('Account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.CTPAccount')),
            ],
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('Name', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('Command', models.CharField(max_length=100)),
                ('LogFile', models.CharField(max_length=100)),
                ('Status', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('Name', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('Command', models.CharField(max_length=100)),
                ('LogFile', models.CharField(max_length=100)),
                ('Crontab', models.CharField(max_length=100)),
                ('Activated', models.BooleanField()),
            ],
        ),
        migrations.AddField(
            model_name='ctporder',
            name='OrderID',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='api.Order'),
        ),
        migrations.AddIndex(
            model_name='ctporder',
            index=models.Index(fields=['FrontID', 'SessionID', 'OrderRef'], name='api_ctporde_FrontID_73ca46_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='ctporder',
            unique_together={('FrontID', 'SessionID', 'OrderRef')},
        ),
    ]
