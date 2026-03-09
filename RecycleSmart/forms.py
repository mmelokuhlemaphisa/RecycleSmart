from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Email, ValidationError, Length


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[('user', 'User'), ('admin', 'Admin')], validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')



class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RecyclingSubmitForm(FlaskForm):
    # Choices will be set dynamically in the submit() route in app.py
    material = SelectField('Material Category', choices=[], validators=[DataRequired()])
    weight = FloatField('Weight (kg)', validators=[DataRequired()])
    description = TextAreaField('Description (Optional)', validators=[Length(max=200)])
    submit = SubmitField('Submit Recycling')


class AdminApprovalForm(FlaskForm):
    # This form will be manually handled in the route, but define structure for completeness
    action = SelectField('Action', choices=[('approve', 'Approve'), ('reject', 'Reject')], validators=[DataRequired()])
    submit = SubmitField('Process Submission')