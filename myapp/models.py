from django.db import models
from django.contrib.auth.models import User

from django.utils import timezone
# class ChatMessage(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     room_name = models.CharField(max_length=255)
#     message = models.TextField(null=True,blank=True)
#     timestamp = models.DateTimeField(auto_now_add=True)

    # def __str__(self):
    #     return f"{self.user.username} in {self.room_name}: {self.message[:30]}"

class Requirements(models.Model):
    loading_point=models.CharField(max_length=100,null=True,blank=True)
    unloading_point=models.CharField(max_length=100,null=True,blank=True)

    loading_point_full_address=models.TextField(null=True,blank=True)
    unloading_point_full_address=models.TextField(null=True,blank=True)

    product = models.CharField(max_length=100,null=True,blank=True)
    truck_type=models.CharField(max_length=100,null=True,blank=True)
    # qty=models.IntegerField(default=0,null=True,blank=True)
    no_of_trucks=models.IntegerField(null=True,blank=True)
    notes=models.TextField(null=True,blank=True)
    drum_type_no_of_drums=models.CharField(max_length=100,null=True,blank=True)
    approx_mat_mt=models.FloatField(null=True,blank=True,default=0)
    weight_per_drum=models.FloatField(null=True,blank=True)
    types=models.CharField(max_length=100,null=True,blank=True)
    cel_price = models.IntegerField(null=True, blank=True)
    min_dec_val = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f" From {self.loading_point}  to {self.unloading_point} Truck: {self.truck_type} {self.truck_type}  Material:{self.product}"

class Bid(models.Model):

    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='bid_user',null=True,blank=True)
    req= models.ForeignKey(Requirements, on_delete=models.DO_NOTHING,related_name='bid_req',null=True,blank=True)
    rate=models.FloatField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f" Trans: {self.user.username}   {self.req} Bid amt:  {self.rate}"


class UserAccess(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,null=True,blank=True)
    requirement_from_access = models.OneToOneField(Requirements, on_delete=models.CASCADE,null=True,blank=True)
    can_view_requirements = models.BooleanField(default=False)


    def __str__(self):
        return f"{self.user.username} access: {self.can_view_requirements}"

class GeneralAccess(models.Model):
    general_access=models.BooleanField(default=False)
    minutes = models.IntegerField(default=0)
    start_time = models.DateTimeField(null=True, blank=True)
    use_cel = models.BooleanField(default=True,null=True,blank=True)

    def __str__(self):
        return f"{self.general_access,self.minutes,self.start_time}"

from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile_no = models.CharField(max_length=15)
    company_name = models.CharField(max_length=200)
    address = models.TextField()
    gst_no = models.CharField(max_length=15)
    pan_no = models.CharField(max_length=10)
    def __str__(self):
        return f"{self.user.username} Profile"
