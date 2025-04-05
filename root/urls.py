from django.contrib import admin
from django.urls import path

from myapp.views import AuthFormView, HomeListView, SettingsFormView, ProfileFormView, district_list_view, \
        ChangePasswordFormView, logout_view, ProductListView, WishlistView, ProductDetailView, LikeListView, \
        OrderFormView, OrderListView, SearchView, MarketView, CreateStreamView, StreamListView, StatsView, \
        CompetitionListView, StreamOrderView, OrderSuccessView, WithdrawView, DiagramView, OperatorTemplateView, \
        OperatorOrderChangeDetailView
from django.conf import settings
from django.conf.urls.static import static
from myapp.views import register_view
urlpatterns = [
        path('admin/', admin.site.urls),
        path('auth', AuthFormView.as_view(), name='auth'),
        path("register/", register_view, name="register"),
        path("profile/settings/", SettingsFormView.as_view(), name="settings"),
        path("profile/", ProfileFormView.as_view(), name="profile"),
        path("district-list/", district_list_view, name="district-list"),
        path("change-password/", ChangePasswordFormView.as_view(), name="change-password"),
        path("logout/", logout_view, name="logout"),
        path("search/", SearchView.as_view(), name="search"),

        path('market', MarketView.as_view(), name='market'),
]

urlpatterns += [
        path('', HomeListView.as_view(), name='home'),
        path("category/<str:slug>", ProductListView.as_view(), name="product-list"),
        path("wishlist/<int:product_id>", WishlistView.as_view(), name="product-list"),
        path("wishlist/", LikeListView.as_view(), name="wish-list"),
        path("product/detail/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
]

urlpatterns += [
        path("order/form/<int:pk>/", OrderFormView.as_view(), name="order"),
        path('orders/list', OrderListView.as_view(), name='order-list'),
        path('order/success/', OrderSuccessView.as_view(), name='order_success'),

]

urlpatterns += [
        path('create-stream/', CreateStreamView.as_view(), name='create-stream'),
        path('streams/', StreamListView.as_view(), name='stream-list'),
        path('stream/<int:stream_id>/order/', StreamOrderView.as_view(), name='stream-order'),
        path('stats/', StatsView.as_view(), name='stats'),
        path('market', MarketView.as_view(), name='market'),
        path('contest/', CompetitionListView.as_view(), name='contest'),
]

urlpatterns += [
        path('withdraw/', WithdrawView.as_view(), name='withdraw'),
        path('diagram/', DiagramView.as_view(), name='diagram'),
        path('operator', OperatorTemplateView.as_view(), name='operator'),
        path('operator-list/', OperatorTemplateView.as_view(), name='operator_list'),
        path("operator/order-change/<int:pk>", OperatorOrderChangeDetailView.as_view(), name="order-change")

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

