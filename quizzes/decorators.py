from django.http import HttpResponseForbidden


def staff_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser and not request.user.is_staff:
            return HttpResponseForbidden("Vous n'avez pas accès à cette page.")
        return view_func(request, *args, **kwargs)
    return wrapper

