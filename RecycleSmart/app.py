from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime

# Import Forms
from forms import RegistrationForm, LoginForm, RecyclingSubmitForm, AdminApprovalForm

# --- 1. INITIALIZATION & CONFIGURATION ---
app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recyclesmart.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'RecycleSmart_Group11_Dev_2026!'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


# --- 2. DATABASE MODELS ---

class User(db.Model, UserMixin):
    __tablename__ = 'user'

    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(120), unique=True, nullable=False)
    user_password = db.Column(db.String(150), nullable=False)
    user_role = db.Column(db.String(20), default='user', nullable=False)
    user_join_date = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow)

    recycling_entries = db.relationship(
        'RecyclingEntry', backref='user', lazy=True)
    point_ledgers = db.relationship('PointLedger', backref='user', lazy=True)

    def set_password(self, password):
        self.user_password = bcrypt.generate_password_hash(
            password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.user_password, password)

    def is_admin(self):
        return self.user_role == 'admin'

    def get_id(self):
        return str(self.user_id)


class MaterialType(db.Model):
    __tablename__ = 'material_type'

    material_type_id = db.Column(db.Integer, primary_key=True)
    material_type_name = db.Column(db.String(50), nullable=False, unique=True)
    points_per_kg = db.Column(db.Float, nullable=False)

    recycling_entries = db.relationship(
        'RecyclingEntry', backref='material_type', lazy=True)


class RecyclingEntry(db.Model):
    __tablename__ = 'recycling_entry'

    entry_id = db.Column(db.Integer, primary_key=True)
    entry_weight = db.Column(db.Float, nullable=False)
    entry_date = db.Column(db.DateTime, nullable=False,
                           default=datetime.utcnow)
    entry_status = db.Column(db.String(20), default='pending', nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey(
        'user.user_id'), nullable=False)
    material_type_id = db.Column(db.Integer, db.ForeignKey(
        'material_type.material_type_id'), nullable=False)

    point_ledger_entry = db.relationship(
        'PointLedger', backref='entry', uselist=False, lazy=True)


class PointLedger(db.Model):
    __tablename__ = 'point_ledger'

    points_ledger_id = db.Column(db.Integer, primary_key=True)
    points_awarded = db.Column(db.Integer, nullable=False)
    points_ledger_date_awarded = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey(
        'user.user_id'), nullable=False)
    entry_id = db.Column(db.Integer, db.ForeignKey(
        'recycling_entry.entry_id'), unique=True, nullable=False)


# --- 3. LOGIN MANAGER ---

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'MaterialType': MaterialType,
        'RecyclingEntry': RecyclingEntry,
        'PointLedger': PointLedger
    }


# --- 4. ROUTES ---

# LANDING PAGE
@app.route("/")
def index():
    return render_template("index.html")


# REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():

    form = RegistrationForm()

    if form.validate_on_submit():

        user_exists = User.query.filter_by(user_email=form.email.data).first()

        if user_exists:
            flash('That email is already registered.', 'danger')
            return render_template('register.html', title='Register', form=form)

        user = User(
            user_name=form.username.data,
            user_email=form.email.data,
            user_role=form.role.data
        )

        user.set_password(form.password.data)

        if not User.query.filter_by(user_role='admin').first():
            user.user_role = 'admin'
            flash('First admin account created!', 'success')

        db.session.add(user)
        db.session.commit()

        flash('Account created successfully. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', title='Register', form=form)


# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():

    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()

    if form.validate_on_submit():

        user = User.query.filter_by(user_email=form.email.data).first()

        if user and user.check_password(form.password.data):

            login_user(user, remember=True)

            next_page = request.args.get('next')

            return redirect(next_page) if next_page else redirect(url_for('dashboard'))

        elif not user:
            flash('User not found.', 'danger')

        else:
            flash('Incorrect password.', 'danger')

    return render_template('login.html', title='Login', form=form)


# LOGOUT
@app.route("/logout")
@login_required
def logout():

    logout_user()

    flash("You have been logged out.", 'info')

    return redirect(url_for('index'))


# DASHBOARD
@app.route("/dashboard")
@login_required
def dashboard():

    total_points = db.session.query(db.func.sum(PointLedger.points_awarded))\
        .filter_by(user_id=current_user.user_id).scalar()

    total_points = total_points if total_points else 0

    user_entries = RecyclingEntry.query.filter_by(user_id=current_user.user_id)\
        .order_by(RecyclingEntry.entry_date.desc()).all()

    return render_template(
        'dashboard.html',
        title='Dashboard',
        total_points=total_points,
        entries=user_entries
    )


# SUBMIT RECYCLING
@app.route("/submit", methods=['GET', 'POST'])
@login_required
def submit():

    material_choices = [
        (mt.material_type_id,
         f"{mt.material_type_name} ({mt.points_per_kg} pts/kg)")
        for mt in MaterialType.query.all()
    ]

    form = RecyclingSubmitForm(
        material=material_choices[0][0] if material_choices else None
    )

    form.material.choices = material_choices

    if form.validate_on_submit():

        new_entry = RecyclingEntry(
            entry_weight=form.weight.data,
            user_id=current_user.user_id,
            material_type_id=form.material.data,
            entry_status='pending'
        )

        db.session.add(new_entry)
        db.session.commit()

        flash('Recycling submission logged. Awaiting admin approval.', 'success')

        return redirect(url_for('dashboard'))

    return render_template('submit.html', title='Submit Recycling', form=form)


# ADMIN REVIEW
@app.route("/admin/review", methods=['GET', 'POST'])
@login_required
def admin_review():

    if not current_user.is_admin():
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))

    pending_entries = RecyclingEntry.query.filter_by(
        entry_status='pending').all()

    form = AdminApprovalForm()

    if request.method == 'POST':

        entry_id = request.form.get('entry_id')
        action = request.form.get('action')

        entry = RecyclingEntry.query.get_or_404(entry_id)

        if action == 'approve':

            points = int(entry.entry_weight *
                         entry.material_type.points_per_kg)

            entry.entry_status = 'approved'

            ledger = PointLedger(
                user_id=entry.user_id,
                entry_id=entry.entry_id,
                points_awarded=points
            )

            db.session.add(ledger)

            flash(f'{points} points awarded.', 'success')

        elif action == 'reject':

            entry.entry_status = 'rejected'

            flash('Entry rejected.', 'warning')

        db.session.commit()

        return redirect(url_for('admin_review'))

    return render_template(
        'admin_review.html',
        title='Admin Review',
        entries=pending_entries,
        form=form
    )


# --- 5. RUN APPLICATION ---

if __name__ == '__main__':

    with app.app_context():

        db.create_all()

        print("Database initialized")

        if not User.query.filter_by(user_role='admin').first():

            admin_user = User(
                user_name='Admin User',
                user_email='admin@dut.ac.za',
                user_role='admin'
            )

            admin_user.set_password('AdminPass123')

            db.session.add(admin_user)
            db.session.commit()

            print("Admin account created")

    app.run(debug=True, host='0.0.0.0', port=8081)
