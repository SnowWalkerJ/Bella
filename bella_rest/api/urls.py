from django.conf.urls import url
from rest_framework.routers import DefaultRouter
from rest_framework.schemas import get_schema_view

from . import views

schema_view = get_schema_view()

router = DefaultRouter()
router.register("ctp", views.CTPAccountViewSet, "CtpAccount")
router.register("service", views.ServiceViewSet, "Service")
router.register("task", views.TaskViewSet, "Task")
router.register("order", views.OrderViewSet, "Order")
router.register("ctp_order", views.CTPOrderViewSet, "CTPOrder")
router.register("ctp_trade", views.CTPTradeViewSet, "CTPTrader")
router.register("tradebot", views.TradeBotViewSet, "TradeBot")

urlpatterns = router.urls
urlpatterns += [
    url(r"^schema$", schema_view),
    url(r"^instruments", views.InstrumentView.as_view()),
    url(r"^query_order_from_ctporder/(?P<session_id>[^/.]+)/(?P<front_id>[^/.]+)/(?P<order_ref>[^/.]+)/$", views.QueryOrderFromCTPOrder.as_view()),
    url(r"^position/(?P<pk>[^/.]+)/$", views.Position.as_view()),
    url(r"^ctp_order/(?P<session_id>[^/.]+)/(?P<front_id>[^/.]+)/(?P<order_ref>[^/.]+)/$", views.CTPOrderDetailView.as_view()),
]
