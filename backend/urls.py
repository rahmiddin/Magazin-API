from django.urls import path
from .views import RegisterAccount, ConfirmAccount, LoginAccount, PartnerUpdate, BasketView, CategoryView, \
    ShopView, ProductInfoView

urlpatterns = [
    path('user/register', RegisterAccount.as_view(), name='user_register'),
    path('user/login', LoginAccount.as_view(), name='user_login'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('basket', BasketView.as_view(), name='basket'),
    path('category', CategoryView.as_view(), name='category'),
    path('shop', ShopView.as_view(), name='shop'),
    path('products', ProductInfoView.as_view(), name='shops'),
]
