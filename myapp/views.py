# myapp/views.py
from django.contrib.auth import authenticate, login, logout
import csv

from django.contrib.auth.decorators import login_required

from .models import Requirements
from django.views.decorators.csrf import csrf_exempt
import json
# views.py
from django.shortcuts import redirect
from django.contrib import messages
from .models import Bid
def index(request):
    # If logged in, go to dashboard
    if request.user.is_authenticated:
        # print("The User from views:", request.user.is_superuser)
        if request.user.is_superuser:
            requirements = Requirements.objects.all()
            # print("The Requirements from views:", requirements)

            return render(request, "myapp/admin_dashboard.html", {"requirements": requirements})

            # return render(request,'myapp/admin_dashboard.html')
        elif request.user.is_staff:
            return render(request, "myapp/staff_dashboard.html")

        else:
            return render(request, 'myapp/index.html')
    return redirect('login')  # Otherwise show login

#
# def register_view(request):
#     if request.method == 'POST':
#         username = request.POST['username']
#         password = request.POST['password']
#
#         if User.objects.filter(username=username).exists():
#             messages.error(request, 'Username already exists.')
#             return redirect('register')
#
#
#         user = User.objects.create_user(username=username, password=password)
#         login(request, user)
#         return redirect('index')
#
#     return render(request, 'myapp/register.html')


from django.contrib.auth.models import User
from .models import Profile

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        mobile_no = request.POST['mobile_no']
        company_name = request.POST['company_name']
        address = request.POST['address']
        email = request.POST['email']
        gst_no = request.POST['gst_no']
        pan_no = request.POST['pan_no']

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')

        # Create User
        user = User.objects.create_user(username=username, password=password, email=email)

        # Create Profile
        Profile.objects.create(
            user=user,
            mobile_no=mobile_no,
            company_name=company_name,
            address=address,
            gst_no=gst_no,
            pan_no=pan_no
        )

        login(request, user)
        return redirect('index')

    return render(request, 'myapp/register.html')



def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        if not User.objects.filter(username=username).exists():
            messages.error(request, 'User does not exist register new account.')
            return redirect('login')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, 'Invalid credentials')
            return redirect('login')
    return render(request, 'myapp/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')

@login_required(login_url='/login/')
def create_requirement(request):
    if request.method == "POST":
        loading_point = request.POST.get("loading_point")
        unloading_point = request.POST.get("unloading_point")
        loading_point_full_address = request.POST.get("loading_point_full_address")
        unloading_point_full_address = request.POST.get("unloading_point_full_address")

        truck_type = request.POST.get("truck_type")
        no_of_trucks=request.POST.get("no_of_trucks")
        # qty = request.POST.get("qty")
        product = request.POST.get("product")
        notes = request.POST.get("notes")
        drum_type_no_of_drums = request.POST.get("drum_type_no_of_drums")
        weight_per_drum = request.POST.get("weight_per_drum")
        approx_mat_mt = request.POST.get("approx_mat_mt")
        types = request.POST.get("types")
        cel_price= request.POST.get("cel_price")
        min_dec_val= request.POST.get("min_dec_val")
        Requirements.objects.create(loading_point=loading_point, unloading_point=unloading_point,loading_point_full_address=loading_point_full_address,unloading_point_full_address=unloading_point_full_address, truck_type=truck_type,no_of_trucks=no_of_trucks,
                                     product=product,notes=notes, drum_type_no_of_drums=drum_type_no_of_drums,weight_per_drum=weight_per_drum,approx_mat_mt=approx_mat_mt,types=types,cel_price=cel_price,min_dec_val=min_dec_val)
        return redirect('requirements')  # <-- Redirect to avoid re-submission on refresh

    requirements = Requirements.objects.all()
    # print("All requirements:", requirements)
    return render(request, "myapp/admin_dashboard.html", {"requirements": requirements})  # Or render to the dashboard



@login_required(login_url='/login/')
def del_requirement(request):
    '''
    Return JsonResponse instead of rendering the template:

You're calling this from JavaScript fetch(), not through a form submission. So you should return JSON, not an HTML page.

    '''
    if request.method == "POST":
        reqid = request.POST.get("reqId")
        # print("reqid in view delete:",reqid)
        if reqid == 'delAll':
            Requirements.objects.all().delete()
            return JsonResponse({"status": "success", "message": f" All Requirement  deleted."})
        else:
            try:
                Requirements.objects.filter(id=reqid).delete()
                return JsonResponse({"status": "success", "message": f"Requirement {reqid} deleted."})
            except Exception as e:
                return JsonResponse({"status": "error", "message": str(e)}, status=500)

    else:
        return JsonResponse({"status": "error", "message": "Invalid request method."}, status=400)



@login_required(login_url='/login/')
def download_template(request):
    # Get all field names from the Requirements model (excluding auto fields like id)
    field_names = [field.name for field in Requirements._meta.fields if not field.auto_created]

    # Create HTTP response with CSV content
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=requirements_template.csv'

    writer = csv.writer(response)
    writer.writerow(field_names)  # Write header only

    return response


import pandas as pd
from django.http import HttpResponse

@login_required(login_url='/login/')
def download_requirements(request):
    all_bids = Bid.objects.all().values(
        "id", "user__username", "req__id", "req__loading_point","req__unloading_point","req__product","req__truck_type", "rate", "created_at"
    )
    rank_df = pd.DataFrame(list(all_bids))  # ✅ now it's
    # Pick the lowest rate per user per requirement
    lowest_bids = rank_df.sort_values("rate").groupby(
        ["req__id", "user__username"], as_index=False
    ).first()
    # Rank them within each requirement
    lowest_bids["Rank"] = lowest_bids.groupby("req__id")["rate"].rank(
        ascending=True, method="dense"
    )

    # Keep only ranks 1 to 4
    rank_df = lowest_bids[lowest_bids["Rank"].between(1, 4)]
    # Generate CSV in memory instead of saving file on server
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="Bid.csv"'
    rank_df.to_csv(path_or_buf=response, index=False)
    return response


@login_required(login_url='/login/')
def delete_all_bids(request):
    if request.method == "POST":  # only allow POST for safety
        Bid.objects.all().delete()
        messages.success(request, "All bids have been deleted successfully.")
    return redirect("requirements")  # redirect wherever you want



@login_required(login_url='/login/')
@csrf_exempt
def bulk_upload_requirements(request):
    if request.method == "POST":
        data = json.loads(request.body).get("data", [])
        objs = []
        bulk_upload_exception = []

        for index, row in enumerate(data, start=1):
            try:
                objs.append(Requirements(
                    loading_point=row.get("loading_point", ""),
                    unloading_point=row.get("unloading_point", ""),
                    loading_point_full_address=row.get("loading_point_full_address", ""),
                    unloading_point_full_address=row.get("unloading_point_full_address", ""),
                    product=row.get("product", ""),
                    truck_type=row.get("truck_type", ""),
                    # qty=int(row.get("qty") or 0),
                    no_of_trucks=int(row.get("no_of_trucks") or 0),
                    notes=row.get("notes", ""),
                    drum_type_no_of_drums=row.get("drum_type_no_of_drums", ""),
                    weight_per_drum=float(row.get("weight_per_drum") or 0),
                    approx_mat_mt=float(row.get("approx_mat_mt") or 0),
                    types=row.get("types", ""),
                    cel_price=int(row.get("cel_price")or 0),
                    min_dec_val=int(row.get("min_dec_val")or 0)
                ))
            except Exception as e:
                bulk_upload_exception.append({"index": index, "Exception": str(e)})
                continue

        Requirements.objects.bulk_create(objs)
        new_requirements = [model_to_dict(obj) for obj in objs]

        return JsonResponse({
            "status": "success",
            "count": len(objs),
            "bulk_upload_exception": bulk_upload_exception,
            "new_requirements": new_requirements
        })

    return JsonResponse({"error": "Invalid method"}, status=400)


from django.forms.models import model_to_dict
from django.http import JsonResponse

@login_required(login_url='/login/')
def edit_requirement(request):
    if request.method == "POST":
        reqid = request.POST.get("reqId")
        try:
            requirement = Requirements.objects.get(pk=reqid)  # ✅ Use .get() instead of .filter()
            # print("Edit Requirement:", requirement)
            re=JsonResponse(model_to_dict(requirement))
            # print("Edit Requirement json:", re)
            return JsonResponse(model_to_dict(requirement))
        except Requirements.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Requirement not found"}, status=404)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method."}, status=400)


from django.shortcuts import render
from django.contrib.auth.models import User
from django.http import JsonResponse
from .models import UserAccess
from .models import GeneralAccess
from datetime import datetime
from django.utils.timezone import make_aware
import pytz


@login_required(login_url='/login/')
def admin_dashboard(request):
    if request.method == "POST":
        start_time_str=request.POST.get("start_time")
        minute=request.POST.get("minute")
        # print("Start_time Time:", start_time_str)

        if start_time_str:
            # Parse the datetime-local string into a datetime object
            start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M")

            # Make it timezone-aware in Asia/Kolkata
            india_tz = pytz.timezone('Asia/Kolkata')
            start_time = india_tz.localize(start_time)


            # Store only the time part in the DB
            access, _ = GeneralAccess.objects.get_or_create(id=1)
            access.minutes = minute
            access.start_time = start_time
            access.save()

            # print("Bidding End  Time:", end_time.strftime("%H:%M"))
        selected_usernames = request.POST.getlist("user")
        general_access = request.POST.getlist("access")
        use_cel = request.POST.getlist("use_cel")
        print("use_cel from view:",use_cel)
        # print("General Access  of select field:", general_access)
        if general_access and general_access[0]=="yes":
            '''This is for general singleton GeneralAccess instance'''
            access, _ = GeneralAccess.objects.get_or_create(id=1)
            access.general_access =True
            access.save()
        elif general_access and general_access[0]=="no":
            access, _ = GeneralAccess.objects.get_or_create(id=1)
            access.general_access =False
            access.save()
        else:

            print("No access option selected")

        if general_access and use_cel[0]== "yes":
            '''This is for general singleton GeneralAccess instance'''
            access, _ = GeneralAccess.objects.get_or_create(id=1)
            access.use_cel = True
            access.save()
        elif general_access and use_cel[0] == "no":
            access, _ = GeneralAccess.objects.get_or_create(id=1)
            access.use_cel = False
            access.save()
        else:
            print("No access option selected for ceiling price")

        # access, _ = GeneralAccess.objects.get_or_create(id=1)
        # access.minutes = minute
        # access.end_time = end_time
        # access.save()
        '''This is for individual  and all user access'''
        try:
            all_users = User.objects.filter(is_superuser=False, is_staff=False)
            superusers = User.objects.filter(is_superuser=True)

            for user in all_users:
                user_access, _ = UserAccess.objects.get_or_create(user=user)
                if user.username in selected_usernames:
                    user_access.can_view_requirements = True

                else:
                    user_access.can_view_requirements = False
                user_access.save()

            for user in superusers:
                user_access, _ = UserAccess.objects.get_or_create(user=user)
                user_access.can_view_requirements = True
                user_access.save()


                # bid_end_time=str(end_time.strftime("%H:%M"))
                # channel_layer=get_channel_layer()
                # async_to_sync(channel_layer.group_send)(
                #     "chat_room1",
                #     {
                #         "type": "bid_end_time",
                #         "message": bid_end_time
                #     }
                # )

            # return JsonResponse({"success": True})
            return redirect("/")

        except Exception as e:
            # return JsonResponse({"success": False, "message": str(e)})
            return render(request, "myapp/admin_dashboard.html")
    # On GET: send non-superusers to the template
    # users = User.objects.filter(is_superuser=False,is_staff=False)
    return render(request, "myapp/admin_dashboard.html")
