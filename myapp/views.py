from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.hashers import check_password
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Sum
from django.http import JsonResponse
from django.shortcuts import  redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, FormView, DetailView, UpdateView
from myapp.forms import AuthForm, RegisterForm, ProfileForm, ChangePasswordForm, OrderForm, StreamForm, WithdrawForm, \
    OrderModelForm
from myapp.models import District, Region, Category, Product, Wishlist, Stream, Withdraw
from django.db.models import Count, Q
from django.utils import timezone
from django.shortcuts import render
from datetime import datetime
from django.views.generic import ListView
from .models import User, Order, AdminSetting
from datetime import timedelta
class AuthFormView(FormView):
    form_class = AuthForm
    template_name = 'apps/auth/auth.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        data = form.cleaned_data
        phone_number = data.get('phone_number')
        password = form.data.get('password')
        users = User.objects.filter(phone_number=phone_number)
        if users.exists():
            user = users.first()
            if check_password(password, user.password):
                login(self.request, user)
            else:
                messages.error(self.request, "Password is incorrect !")
                return redirect('auth')
        else:
            user = form.save()
            login(self.request, user)
        return super().form_valid(form)

    def form_invalid(self, form):
        for error in form.errors.values():
            messages.error(self.request, error)
        return super().form_invalid(form)
class HomeListView(ListView):
    queryset = Category.objects.all()
    template_name = "apps/home.html"
    context_object_name = "categories"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['products'] = Product.objects.all()
        data['liked_products_id'] = list(Wishlist.objects.filter(user_id=self.request.user).values_list("product_id", flat=True)) if self.request.user.is_authenticated else []

        return data
class ProfileFormView(TemplateView):
    template_name = 'apps/auth/profile.html'
class SettingsFormView(LoginRequiredMixin, FormView):
    template_name = 'apps/auth/settings.html'
    form_class = ProfileForm
    success_url = reverse_lazy('settings')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['regions'] = Region.objects.all()
        return data

    def form_valid(self, form):
        form.update(self.request.user)
        return super().form_valid(form)

    def form_invalid(self, form):
        print(form.errors)  # Form xatolarini konsolda chiqaramiz
        return self.render_to_response(self.get_context_data(form=form))
class ChangePasswordFormView(LoginRequiredMixin, FormView):
    form_class = ChangePasswordForm
    template_name = 'apps/auth/auth.html'
    success_url = reverse_lazy('settings')

    def form_valid(self, form):
        session_password = self.request.user.password
        old_password = form.cleaned_data.get('old')
        if not check_password(old_password, session_password):
            messages.error(self.request, "Old Password incorrect")
            return self.form_invalid(form)
        else:
            form.update(self.request.user)
            update_session_auth_hash(self.request, self.request.user)  # Keep the user logged in
            messages.success(self.request, "Your password has been changed successfully.")
            return super().form_valid(form)
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Ro'yxatdan o'tish muvaffaqiyatli! Endi tizimga kiring.")
            return redirect("auth")  # Redirect to login page after successful registration
        else:
            print(form.errors)  # Debugging: See the errors in console
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")  # Show specific error messages
    else:
        form = RegisterForm()

    return render(request, "apps/auth/register.html", {"form": form})
def district_list_view(request):
    region_id = request.GET.get('region_id')
    districts = District.objects.filter(region_id=region_id).values("id", "name")
    return JsonResponse(list(districts), safe=False)
def logout_view(request):
    logout(request)
    return redirect("auth")
class ProductListView(ListView):
    template_name = 'apps/menus/product-list.html'
    context_object_name = "products"

    def get_queryset(self):
        slug = self.kwargs.get('slug')
        category = Category.objects.filter(slug=slug).first()

        # If category exists, filter products; otherwise, return all
        if slug and slug != 'all' and category:
            return Product.objects.filter(category=category)
        return Product.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs.get('slug')
        category = Category.objects.filter(slug=slug).first()

        # Handle search functionality
        query = self.request.GET.get('query')
        if query:
            context['products'] = context['products'].filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )

        # Add extra context
        context['categories'] = Category.objects.all()
        context['session_category'] = category

        if self.request.user.is_authenticated:
            context['liked_products_id'] = Wishlist.objects.filter(
                user_id=self.request.user
            ).values_list("product_id", flat=True)

        return context
class WishlistView(LoginRequiredMixin, View):
    login_url = reverse_lazy('auth')

    def get(self, request, product_id):
        liked = True
        like = Wishlist.objects.filter(product_id=product_id, user=self.request.user)
        if like.exists():
            like.delete()
            liked = False
        else:
            Wishlist.objects.create(product_id=product_id, user=self.request.user)

        return JsonResponse({"liked": liked})
class ProductDetailView(DetailView):
    queryset = Product.objects.all()
    template_name = 'apps/order/product-detail.html'
    slug_url_kwarg = "slug"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()  # Retrieve the product
        context['streams'] = Stream.objects.filter(product=product)  # Get streams for the product

        # If no streams are available, add a message and redirect to stream creation
        if not context['streams'].exists():
            messages.warning(self.request, 'No streams available for this product. Please create a stream first.')
            context['redirect_to_create_stream'] = True
        return context

    def post(self, request, *args, **kwargs):
        product = self.get_object()  # Retrieve the product
        # You could handle form submission here (e.g., placing an order, etc.)
        return redirect('product-detail', slug=product.slug)
class LikeListView(ListView):
    queryset = Wishlist.objects.all()
    template_name = 'apps/menus/wish-list.html'
    context_object_name = 'products'

    def get_context_data(self, *, object_list=None, **kwargs):
        data = super().get_context_data(object_list=object_list, **kwargs)
        data['products'] = Product.objects.filter(wishlist__user=self.request.user)
        data['liked_products_id'] = Wishlist.objects.filter(user_id=self.request.user.id).values_list("product_id",
                                                                                                      flat=True)
        return data
class OrderFormView(FormView):
    form_class = OrderForm
    template_name = "apps/order/order-success.html"
    success_url = reverse_lazy("order_success")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['product_id'] = self.kwargs['pk']
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = Product.objects.get(pk=self.kwargs['pk'])
        context['product'] = product
        context['streams'] = Stream.objects.filter(product=product)

        # If the order is created, pass it to the template
        if 'order' in kwargs:
            context['order'] = kwargs['order']
        return context

    def form_valid(self, form):
        """Save order and handle optional stream"""
        user = self.request.user if self.request.user.is_authenticated else None
        # Save the order
        order = form.save(user=user)

        # Instead of passing 'order' as an argument to super(), pass it in the context
        return self.render_to_response(self.get_context_data(order=order))
class OrderListView(LoginRequiredMixin, ListView):
    login_url = reverse_lazy('auth')
    queryset = Order.objects
    template_name = 'apps/order/order-list.html'  # Ensure this template exists
    context_object_name = 'orders'

    def get_context_data(self, *, object_list=None, **kwargs):
        data = super().get_context_data(object_list=object_list, **kwargs)
        data['orders'] = data.get('orders').filter(owner=self.request.user)
        return data
class OrderSuccessView(TemplateView):
    template_name = "apps/order/order-success.html"
class SearchView(View):
    template_name = "apps/base/search.html"  # Path to search.html
    results_template_name = "apps/base/search_results.html"  # Path to search_results.html

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        search_query = request.POST.get("product", "").strip()
        if search_query:
            results = Product.objects.filter(name__icontains=search_query)
        else:
            results = None
        return render(request, self.results_template_name, {
            "search_query": search_query,
            "results": results
        })
class MarketView(ListView):
    queryset = Product.objects.all()
    template_name = "apps/thread/market-list.html"
    context_object_name = "products"

    def get_context_data(self, *, object_list=None, **kwargs):
        data = super().get_context_data(object_list=object_list, **kwargs)
        products = data['products']
        slug = self.request.GET.get('category')
        search_query = self.request.GET.get('q')

        # Handle the category filter
        if slug == 'top':
            products = Product.objects.annotate(order_count=Count(F('orders'))).order_by('-order_count')[:10]
        elif slug == 'all' or not slug:
            products = Product.objects.all()
        elif slug:
            products = Product.objects.filter(category__slug=slug)

        # Handle the search filter
        if search_query:
            products = products.filter(name__icontains=search_query)  # Case-insensitive search by name

        data['products'] = products
        data['categories'] = Category.objects.all()

        return data
class CreateStreamView(View):
    def get(self, request):
        products = Product.objects.all()
        form = StreamForm()
        return render(request, 'apps/thread/market-list.html', {'form': form, 'products': products})

    def post(self, request):
        form = StreamForm(request.POST)

        if form.is_valid():
            stream = form.save(commit=False)

            if request.user.is_authenticated:
                stream.user = request.user
            else:
                messages.error(request, 'You must be logged in to create a stream.')
                return redirect('login')

            product_id = request.POST.get('product')
            try:
                product = Product.objects.get(id=product_id)
                stream.product = product
                stream.save()
                messages.success(request, 'Stream created successfully!')
                # Redirect to a stream-specific order page
                return redirect('stream-order', stream_id=stream.id)
            except Product.DoesNotExist:
                messages.error(request, 'Invalid product selected!')
        else:
            messages.error(request, 'Error creating stream. Please check the form.')

        return redirect('market')
class StreamOrderView(View):
    template_name = 'apps/thread/stream-order.html'

    def get(self, request, stream_id):
        stream = Stream.objects.get(id=stream_id)
        form = OrderForm(initial={'product_id': stream.product.id})
        return render(request, self.template_name, {'form': form, 'stream': stream})

    def post(self, request, stream_id):
        stream = Stream.objects.get(id=stream_id)
        form = OrderForm(request.POST)

        if form.is_valid():
            if not request.user.is_authenticated:
                messages.error(request, 'You must be logged in to place an order.')
                return redirect('login')

            order = form.save(user=request.user)  # No need to pass stream explicitly
            messages.success(request, 'Order placed successfully!')
            return redirect('market')
        else:
            messages.error(request, 'Error placing order. Please check the form.')
            return render(request, self.template_name, {'form': form, 'stream': stream})
class StreamListView(ListView):
    model = Stream
    template_name = 'apps/thread/stream_list.html'
    context_object_name = 'streams'
    paginate_by = 10

    def get_queryset(self):
        return Stream.objects.all().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.all()
        return context
class StatsView(TemplateView):
    template_name = "apps/thread/stream-statistics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        period = self.request.GET.get('period', 'all')

        # Set time range for filtering
        now = timezone.now()
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'last_day':
            start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)
        elif period == 'weekly':
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == 'monthly':
            start_date = now - timedelta(days=30)
            end_date = now
        else:
            start_date = None
            end_date = None

        # Base query for streams with annotations
        streams_query = Stream.objects.annotate(
            order_count=Count('orders'),
            new_count=Count('orders', filter=Q(orders__status=Order.StatusType.NEW)),
            ready_count=Count('orders', filter=Q(orders__status=Order.StatusType.READY_TO_ORDER)),
            deliver_count=Count('orders', filter=Q(orders__status=Order.StatusType.DELIVERING)),
            delivered_count=Count('orders', filter=Q(orders__status=Order.StatusType.DELIVERED)),
            cant_phone_count=Count('orders', filter=Q(orders__status=Order.StatusType.NOT_PICK_UP)),
            canceled_count=Count('orders', filter=Q(orders__status=Order.StatusType.CANCELED)),
            archived_count=Count('orders', filter=Q(orders__status='archived'))
        )

        if start_date and end_date:
            if period == 'last_day':
                streams_query = streams_query.filter(orders__ordered_at__range=[start_date, end_date])
            else:
                streams_query = streams_query.filter(orders__ordered_at__gte=start_date, orders__ordered_at__lte=end_date)

        streams = streams_query.all()
        all_relevant_orders = []

        # Optimize by querying orders once
        orders_query = Order.objects.all()
        if start_date and end_date:
            if period == 'last_day':
                orders_query = orders_query.filter(ordered_at__range=[start_date, end_date])
            else:
                orders_query = orders_query.filter(ordered_at__gte=start_date, ordered_at__lte=end_date)

        # Handle orders with no stream
        no_stream_orders = orders_query.filter(stream__isnull=True)
        all_relevant_orders.extend(no_stream_orders)

        # Calculate totals from all relevant orders
        all_orders = orders_query.filter(id__in=[order.id for order in all_relevant_orders])
        context['streams'] = streams
        context['no_stream_orders'] = {
            'count': no_stream_orders.count(),
            'new_count': no_stream_orders.filter(status=Order.StatusType.NEW).count(),
            'ready_count': no_stream_orders.filter(status=Order.StatusType.READY_TO_ORDER).count(),
            'deliver_count': no_stream_orders.filter(status=Order.StatusType.DELIVERING).count(),
            'delivered_count': no_stream_orders.filter(status=Order.StatusType.DELIVERED).count(),
            'cant_phone_count': no_stream_orders.filter(status=Order.StatusType.NOT_PICK_UP).count(),
            'canceled_count': no_stream_orders.filter(status=Order.StatusType.CANCELED).count(),
            'archived_count': 0,
        }
        context['all_count'] = all_orders.count()
        context['all_new'] = all_orders.filter(status=Order.StatusType.NEW).count()
        context['all_ready'] = all_orders.filter(status=Order.StatusType.READY_TO_ORDER).count()
        context['all_deliver'] = all_orders.filter(status=Order.StatusType.DELIVERING).count()
        context['all_delivered'] = all_orders.filter(status=Order.StatusType.DELIVERED).count()
        context['all_cant_phone'] = all_orders.filter(status=Order.StatusType.NOT_PICK_UP).count()
        context['all_canceled'] = all_orders.filter(status=Order.StatusType.CANCELED).count()
        context['all_archived'] = 0

        context['period'] = period
        return context
class CompetitionListView(ListView):
    template_name = 'apps/menus/competition.html'
    context_object_name = "users"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['site'] = AdminSetting.objects.first()

        if data['users']:
            data['winner'] = max(data['users'], key=lambda u: u['total_quantity'], default=None)
        else:
            data['winner'] = None

        return data

    def get_queryset(self):
        admin_setting = AdminSetting.objects.first()
        if not admin_setting:
            return []

        start_date = datetime.combine(admin_setting.start, datetime.min.time(), tzinfo=timezone.get_current_timezone())
        end_date = datetime.combine(admin_setting.finish, datetime.min.time(), tzinfo=timezone.get_current_timezone())

        print(f"Start Date: {start_date}, End Date: {end_date}")

        # Annotate users with the total quantity of items in completed orders
        query = User.objects.annotate(
            total_quantity=Sum(
                'orders__quantity',
                filter=Q(
                    orders__status=Order.StatusType.COMPLETED,
                    orders__ordered_at__range=[start_date, end_date]
                ),
                default=0
            )
        )

        print("Query: ", str(query.query))

        # Order by total quantity (descending)
        query = query.order_by('-total_quantity').only('first_name', 'last_name', 'phone_number')

        ranked_users = []
        for rank, user in enumerate(query, start=1):
            if user.total_quantity > 0:  # Only include users with at least some quantity
                full_name = f"{user.first_name} {user.last_name}".strip() or user.username or user.phone_number
                ranked_users.append({
                    'rank': rank,
                    'full_name': full_name,
                    'total_quantity': user.total_quantity
                })

        return ranked_users
class WithdrawView(LoginRequiredMixin, FormView):
    template_name = "apps/menus/withdraw.html"
    form_class = WithdrawForm
    success_url = reverse_lazy('withdraw')
    login_url = reverse_lazy("login")

    def form_valid(self, form):
        withdraw = form.save(commit=False)
        user = self.request.user
        request_amounted = withdraw.amount

        if user.balance < request_amounted:
            messages.error(self.request, "Balansingizda hisob yetarli emas")
            return self.form_invalid(form)
        user.balance -= request_amounted
        user.save()
        withdraw.user = user
        withdraw.save()
        messages.success(self.request, "Sorov yuborildi ! ")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["user"] = self.request.user
        data["withdraws"] = Withdraw.objects.filter(user=self.request.user).order_by('-created_at')
        return data
class DiagramView(TemplateView):
    template_name = "apps/menus/diagram.html"
class OperatorTemplateView(TemplateView):
    template_name = "apps/operator/operator-page.html"

    def post(self, request):
        context = self.get_context_data()
        return render(request, 'apps/operator/operator-page.html', context)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        status = self.request.GET.get('status')

        category_id = self.request.POST.get('category_id')
        district_id = self.request.POST.get('district_id')
        data['status'] = Order.StatusType.values
        data['categories'] = Category.objects.all()
        data['regions'] = Region.objects.all()
        orders = Order.objects.filter(status=Order.StatusType.NEW)
        if status:
            orders = Order.objects.filter(status=status)
        if category_id:
            orders = orders.filter(product__category_id=category_id)
        if district_id:
            orders = orders.filter(district_id=district_id)
        data['orders'] = orders
        return data
class OperatorOrderChangeDetailView(DetailView):
    queryset = Order.objects.all()
    template_name = 'apps/operator/order-change.html'
    pk_url_kwarg = 'pk'
    context_object_name = 'order'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['regions'] = Region.objects.all()
        return data

class OrderUpdateView(UpdateView):
    queryset = Order.objects.all()
    form_class = OrderModelForm
    template_name = 'apps/operator/order-change.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('operator')