from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, FloatField, BooleanField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional
from wtforms.widgets import TextArea

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=4)])

class UserForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=4)])
    user_type = SelectField('Tipo de Usuário', choices=[
        ('admin', 'Administrador'),
        ('vendor', 'Vendedor')
    ], validators=[DataRequired()])

class VoucherPlanForm(FlaskForm):
    name = StringField('Nome do Plano', validators=[DataRequired(), Length(min=3, max=200)])
    duration = IntegerField('Duração', validators=[DataRequired(), NumberRange(min=1)])
    duration_unit = SelectField('Unidade de Tempo', choices=[
        ('minutes', 'Minutos'),
        ('hours', 'Horas'),
        ('days', 'Dias')
    ], validators=[DataRequired()])
    price = FloatField('Preço (R$)', validators=[DataRequired(), NumberRange(min=0)])
    data_quota = IntegerField('Franquia de Dados (MB)', validators=[Optional(), NumberRange(min=0)])
    download_speed = IntegerField('Velocidade Download (Mbps)', validators=[Optional(), NumberRange(min=0)])
    upload_speed = IntegerField('Velocidade Upload (Mbps)', validators=[Optional(), NumberRange(min=0)])
    code_length = IntegerField('Comprimento do Código', validators=[DataRequired(), NumberRange(min=6, max=10)], default=8)
    limit_type = SelectField('Tipo de Limite', choices=[
        (0, 'Uso Limitado'),
        (1, 'Usuários Limitados'),
        (2, 'Ilimitado')
    ], validators=[DataRequired()], coerce=int, default=2)
    limit_num = IntegerField('Número do Limite', validators=[Optional(), NumberRange(min=1, max=999)])
    is_active = BooleanField('Ativo', default=True)

class VoucherGenerationForm(FlaskForm):
    plan_id = SelectField('Plano', validators=[DataRequired()], coerce=int)
    quantity = IntegerField('Quantidade', validators=[DataRequired(), NumberRange(min=1, max=1000)])

class OmadaConfigForm(FlaskForm):
    controller_url = StringField('URL do Controller', validators=[DataRequired()])
    client_id = StringField('Client ID', validators=[DataRequired()])
    client_secret = StringField('Client Secret', validators=[DataRequired()])
    omadac_id = StringField('Omadac ID', validators=[DataRequired()])

class CashRegisterForm(FlaskForm):
    notes = TextAreaField('Observações', widget=TextArea(), validators=[Optional(), Length(max=1000)])
    remove_expired = BooleanField('Remover vouchers expirados do Omada Controller', default=True)
