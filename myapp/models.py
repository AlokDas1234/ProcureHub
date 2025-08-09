from django.db import models
from django.contrib.auth.models import User

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room_name = models.CharField(max_length=255)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} in {self.room_name}: {self.message[:30]}"

class Requirements(models.Model):
    loading_point=models.CharField(max_length=100)
    unloading_point=models.CharField(max_length=100)

    loading_point_full_address=models.TextField(null=True,blank=True)
    unloading_point_full_address=models.TextField(null=True,blank=True)

    product = models.CharField(max_length=100)
    truck_type=models.CharField(max_length=100)
    qty=models.IntegerField()
    no_of_trucks=models.IntegerField(null=True,blank=True)
    notes=models.TextField(null=True,blank=True)
    drum_type_no_of_drums=models.CharField(max_length=100,null=True,blank=True)
    weight_per_drum=models.FloatField(null=True,blank=True)
    types=models.CharField(max_length=100,null=True,blank=True)

    def __str__(self):
        return f" From {self.loading_point}  to {self.unloading_point} Truck: {self.truck_type} {self.truck_type} Quantity:{self.qty} Material:{self.product}"

class Bid(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE,related_name='bid_user')
    req= models.ForeignKey(Requirements, on_delete=models.CASCADE,related_name='bid_req')
    rate=models.IntegerField(default=0)

    def __str__(self):
        return f" Trans: {self.user.username}   {self.req} Bid amt:  {self.rate}"


class UserAccess(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    can_view_requirements = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} access: {self.can_view_requirements}"

class GeneralAccess(models.Model):
    general_access=models.BooleanField(default=False)

    def __str__(self):
        return f"{self.general_access}"