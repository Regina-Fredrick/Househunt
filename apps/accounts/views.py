from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from .forms import RegistrationForm
from .models import User


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            domain = get_current_site(request).domain
            link = f'http://{domain}/accounts/verify/{uid}/{token}/'

            subject = 'Verify your Househunt account'
            message = f'Hi {user.username}, click the link to verify your account: {link}'
            send_mail(subject, message, None, [user.email])

            return render(request, 'accounts/check_email.html')
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def verify_email_view(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        return redirect('profile')
    else:
        return render(request, 'accounts/verify_invalid.html')


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})
