from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import User, Business
import re


class LoginForm(forms.Form):
    """Formulario de login personalizado"""
    
    username = forms.CharField(
        label='Usuario',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu usuario',
            'autocomplete': 'username',
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingresa tu contraseña',
            'autocomplete': 'current-password'
        })
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError('El usuario es requerido.')
        return username.strip()


class RegisterBusinessForm(forms.ModelForm):
    """Formulario para registrar un nuevo negocio"""
    
    class Meta:
        model = Business
        fields = ['name', 'email', 'phone', 'address', 'max_concurrent_users']
        labels = {
            'name': 'Nombre del negocio',
            'email': 'Email de contacto',
            'phone': 'Teléfono',
            'address': 'Dirección',
            'max_concurrent_users': 'Usuarios simultáneos'
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Dulcería San José',
                'maxlength': 100
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contacto@minegocio.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '555-123-4567',
                'maxlength': 15
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Dirección completa del negocio',
                'rows': 3
            }),
            'max_concurrent_users': forms.Select(
                choices=[(2, '2 usuarios - $400/mes'), (3, '3 usuarios - $600/mes'), 
                        (5, '5 usuarios - $1,000/mes'), (10, '10 usuarios - $2,000/mes')],
                attrs={'class': 'form-control'}
            )
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise ValidationError('El nombre del negocio es requerido.')
        
        # Verificar que no exista otro negocio con el mismo nombre
        if Business.objects.filter(name__iexact=name.strip()).exists():
            raise ValidationError('Ya existe un negocio con este nombre.')
        
        return name.strip()
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError('El email es requerido.')
        
        # Verificar que no exista otro negocio con el mismo email
        if Business.objects.filter(email__iexact=email.strip()).exists():
            raise ValidationError('Ya existe un negocio registrado con este email.')
        
        return email.strip().lower()
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            # Limpiar el teléfono (solo números, guiones y espacios)
            phone_clean = re.sub(r'[^\d\-\s\+\(\)]', '', phone)
            if len(phone_clean) < 10:
                raise ValidationError('El teléfono debe tener al menos 10 dígitos.')
        return phone
    
    def clean_max_concurrent_users(self):
        users = self.cleaned_data.get('max_concurrent_users')
        if users < 1:
            raise ValidationError('Debe permitir al menos 1 usuario.')
        if users > 50:
            raise ValidationError('Máximo 50 usuarios simultáneos.')
        return users


class RegisterUserForm(UserCreationForm):
    """Formulario para registrar el usuario propietario del negocio"""
    
    first_name = forms.CharField(
        label='Nombre',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu nombre'
        })
    )
    
    last_name = forms.CharField(
        label='Apellido',
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu apellido'
        })
    )
    
    email = forms.EmailField(
        label='Email personal',
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'tu_email@ejemplo.com'
        })
    )
    
    phone = forms.CharField(
        label='Teléfono personal',
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '555-123-4567'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de usuario único'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalizar campos de contraseña
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Contraseña segura'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirma tu contraseña'
        })
        
        # Personalizar labels
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Confirmar contraseña'
        self.fields['username'].label = 'Nombre de usuario'
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError('El nombre de usuario es requerido.')
        
        username = username.strip().lower()
        
        # Validar formato de username
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise ValidationError('El usuario solo puede contener letras, números y guión bajo.')
        
        if len(username) < 3:
            raise ValidationError('El usuario debe tener al menos 3 caracteres.')
        
        # Verificar que no exista
        if User.objects.filter(username=username).exists():
            raise ValidationError('Este nombre de usuario ya está en uso.')
        
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError('El email es requerido.')
        
        email = email.strip().lower()
        
        # Verificar que no exista otro usuario con el mismo email
        if User.objects.filter(email=email).exists():
            raise ValidationError('Ya existe un usuario registrado con este email.')
        
        return email
    
    def clean_first_name(self):
        name = self.cleaned_data.get('first_name')
        if not name:
            raise ValidationError('El nombre es requerido.')
        return name.strip().title()
    
    def clean_last_name(self):
        name = self.cleaned_data.get('last_name')
        if not name:
            raise ValidationError('El apellido es requerido.')
        return name.strip().title()
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            # Limpiar el teléfono
            phone_clean = re.sub(r'[^\d\-\s\+\(\)]', '', phone)
            if len(phone_clean) < 10:
                raise ValidationError('El teléfono debe tener al menos 10 dígitos.')
        return phone


class EditUserForm(forms.ModelForm):
    """Formulario para editar información del usuario"""
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Email',
            'phone': 'Teléfono'
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'})
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError('El email es requerido.')
        
        email = email.strip().lower()
        
        # Verificar que no exista otro usuario con el mismo email (excepto el actual)
        existing_user = User.objects.filter(email=email).exclude(pk=self.instance.pk).first()
        if existing_user:
            raise ValidationError('Ya existe otro usuario con este email.')
        
        return email


class ChangePasswordForm(forms.Form):
    """Formulario para cambiar contraseña"""
    
    current_password = forms.CharField(
        label='Contraseña actual',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Tu contraseña actual'
        })
    )
    
    new_password1 = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nueva contraseña segura'
        })
    )
    
    new_password2 = forms.CharField(
        label='Confirmar nueva contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirma la nueva contraseña'
        })
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise ValidationError('La contraseña actual no es correcta.')
        return current_password
    
    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError('Las contraseñas no coinciden.')
            
            # Validar seguridad de la contraseña
            try:
                validate_password(password1, self.user)
            except ValidationError as e:
                raise ValidationError(e.messages)
        
        return password2
    
    def save(self):
        password = self.cleaned_data['new_password1']
        self.user.set_password(password)
        self.user.save()
        return self.user


class BusinessSettingsForm(forms.Form):
    """Formulario para configuraciones del negocio"""
    
    # Información básica
    business_name = forms.CharField(
        label='Nombre del negocio',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    business_email = forms.EmailField(
        label='Email del negocio',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    business_phone = forms.CharField(
        label='Teléfono del negocio',
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    business_address = forms.CharField(
        label='Dirección',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    
    # Configuraciones funcionales
    enable_custom_rounding = forms.BooleanField(
        label='Activar redondeo personalizado',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    send_daily_reports = forms.BooleanField(
        label='Enviar reportes diarios por correo',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    report_email = forms.EmailField(
        label='Email para reportes',
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'reportes@minegocio.com'
        })
    )
    
    show_low_stock_alerts = forms.BooleanField(
        label='Mostrar alertas de stock bajo',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_report_email(self):
        send_reports = self.cleaned_data.get('send_daily_reports')
        report_email = self.cleaned_data.get('report_email')
        
        if send_reports and not report_email:
            raise ValidationError('El email para reportes es requerido si activas el envío automático.')
        
        return report_email