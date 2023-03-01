from django.urls import path, include
from .views import RegisterAccount, ConfirmAccount, LoginAccount, PartnerUpdate, BasketView, CategoryView, \
    ShopView, ProductInfoView, PartnerOrderView, ShopStatusView, ContactView, OrderStatusView, AccountDetailsView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

router.register(r'detail', AccountDetailsView, basename='user-details')

urlpatterns = [
    path('user/', include(router.urls)),
    path('user/register', RegisterAccount.as_view(), name='user_register'),
    path('user/login', LoginAccount.as_view(), name='user_login'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('partner/state', ShopStatusView.as_view(), name='partner-state'),
    path('user/contacts', ContactView.as_view(), name='contacts'),
    path('partner/order', PartnerOrderView.as_view(), name='order'),
    path('basket', BasketView.as_view(), name='basket'),
    path('category', CategoryView.as_view(), name='category'),
    path('shop', ShopView.as_view(), name='shop'),
    path('products', ProductInfoView.as_view(), name='shops'),
    path('order', OrderStatusView.as_view(), name='order'),

]
