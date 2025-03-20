from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime, timedelta
import json
from decimal import Decimal
import io
import xlsxwriter

app = Flask(__name__)
app.secret_key = 'd7b07384d113edec47eaa6238ad5ff00'  # New secret key

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

app.json_encoder = CustomJSONEncoder

@app.template_filter('tojson')
def tojson_filter(obj):
    return json.dumps(obj, cls=CustomJSONEncoder)

def get_db_connection():
    conn = sqlite3.connect('crud_system.db', timeout=20)  # Add timeout
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['enduser'] = user['enduser']
        return redirect(url_for('dashboard'))
    
    flash('Invalid username or password')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get current month's data
    current_month = datetime.now().strftime('%Y-%m')
    current_month_data = conn.execute('''
        SELECT COUNT(*) as count, COALESCE(SUM(Amount), 0) as total_amount
        FROM entry
        WHERE strftime('%Y-%m', "Date Entry") = ?
    ''', (current_month,)).fetchone()
    
    # Get last month's data for comparison
    last_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m')
    last_month_data = conn.execute('''
        SELECT COUNT(*) as count, COALESCE(SUM(Amount), 0) as total_amount
        FROM entry
        WHERE strftime('%Y-%m', "Date Entry") = ?
    ''', (last_month,)).fetchone()
    
    # Get total entries
    total_entries = conn.execute('SELECT COUNT(*) as count FROM entry').fetchone()
    
    # Get last JEV
    last_jev = conn.execute('SELECT JEV FROM entry ORDER BY "Date Entry" DESC LIMIT 1').fetchone()
    
    conn.close()
    
    # Calculate percentage changes
    inputs_change = 0
    amount_change = 0
    
    if last_month_data['count'] > 0:
        inputs_change = ((current_month_data['count'] - last_month_data['count']) / last_month_data['count']) * 100
    if last_month_data['total_amount'] > 0:
        amount_change = ((current_month_data['total_amount'] - last_month_data['total_amount']) / last_month_data['total_amount']) * 100
    
    analytics = {
        'inputs_this_month': current_month_data['count'],
        'total_inputs': total_entries['count'],
        'total_amount': current_month_data['total_amount'],
        'last_jev': last_jev['JEV'] if last_jev else 'No entries yet',
        'inputs_change': round(inputs_change, 1),
        'amount_change': round(amount_change, 1)
    }
    
    return render_template('dashboard.html', analytics=analytics)

@app.route('/accounts')
def accounts():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    conn.close()
    return render_template('accounts.html', users=users)

@app.route('/database')
def database():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    # Get filter parameters
    filter_field = request.args.get('field', 'all')
    filter_value = request.args.get('value', '')
    
    # Base query
    query = 'SELECT * FROM entry'
    params = []
    
    # Apply filters if value is provided
    if filter_value:
        if filter_field == 'all':
            # Search across all relevant fields
            query += ''' WHERE (
                JEV LIKE ? OR 
                Payee LIKE ? OR 
                ObligationRequest LIKE ? OR 
                COALESCE(AccountsPayable, '') LIKE ? OR 
                Particulars LIKE ? OR 
                CAST(Amount AS TEXT) LIKE ? OR
                "Date Entry" LIKE ? OR 
                COALESCE("Date Received", '') LIKE ?
            )'''
            search_term = f'%{filter_value}%'
            params.extend([search_term] * 8)
        else:
            # Field-specific search
            if filter_field == 'amount':
                try:
                    # Try exact match for amount
                    amount = float(filter_value)
                    query += ' WHERE Amount = ?'
                    params.append(amount)
                except ValueError:
                    # If not a valid number, search as string
                    query += ' WHERE CAST(Amount AS TEXT) LIKE ?'
                    params.append(f'%{filter_value}%')
            elif filter_field in ['entryDate', 'receivedDate']:
                # Handle date fields
                field_name = '"Date Entry"' if filter_field == 'entryDate' else '"Date Received"'
                query += f' WHERE {field_name} LIKE ?'
                params.append(f'%{filter_value}%')
            else:
                # Handle text fields
                field_mapping = {
                    'jev': 'JEV',
                    'payee': 'Payee',
                    'obligationRequest': 'ObligationRequest',
                    'accountsPayable': 'AccountsPayable',
                    'particulars': 'Particulars'
                }
                field_name = field_mapping.get(filter_field)
                if field_name:
                    query += f' WHERE {field_name} LIKE ?'
                    params.append(f'%{filter_value}%')
    
    # Add ORDER BY clause
    query += ' ORDER BY "Date Entry" DESC'
    
    # Execute query with parameters
    entries = [dict(row) for row in conn.execute(query, params).fetchall()]
    
    # Format dates for display
    for entry in entries:
        if entry['Date Entry']:
            try:
                date_entry = datetime.strptime(entry['Date Entry'], '%Y-%m-%d %H:%M:%S')
                entry['Date Entry'] = date_entry.strftime('%Y-%m-%d')
            except ValueError:
                entry['Date Entry'] = entry['Date Entry'].split()[0]
        
        if entry['Date Received']:
            try:
                date_received = datetime.strptime(entry['Date Received'], '%Y-%m-%d %H:%M:%S')
                entry['Date Received'] = date_received.strftime('%Y-%m-%d')
            except ValueError:
                entry['Date Received'] = entry['Date Received'].split()[0]
    
    conn.close()
    return render_template('database.html', entries=entries)

@app.route('/submit_entry', methods=['POST'])
def submit_entry():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    conn = None
    try:
        jev = request.form['jev']
        payee = request.form['payee']
        obligation_request = request.form['obligationRequest']
        accounts_payable = request.form['accountsPayable'] if request.form['accountsPayable'] else None
        particulars = request.form['particulars']
        amount = float(request.form['amount'])
        entry_date = request.form['entryDate']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO entry (JEV, Payee, ObligationRequest, AccountsPayable, Particulars, Amount, "Date Entry")
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (jev, payee, obligation_request, accounts_payable, particulars, amount, entry_date))
        conn.commit()
        flash('Entry submitted successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('Error: JEV number already exists!', 'error')
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            flash('Database is busy. Please try again in a moment.', 'error')
        else:
            flash(f'Database error: {str(e)}', 'error')
    except Exception as e:
        flash(f'Error submitting entry: {str(e)}', 'error')
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/update_entry', methods=['POST'])
def update_entry():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        jev = request.form.get('jev')
        payee = request.form.get('payee')
        obligation_request = request.form.get('obligationRequest')
        accounts_payable = request.form.get('accountsPayable')
        particulars = request.form.get('particulars')
        amount = float(request.form.get('amount'))
        date_received = request.form.get('dateReceived')
        
        conn = get_db_connection()
        conn.execute('''
            UPDATE entry 
            SET Payee = ?, ObligationRequest = ?, AccountsPayable = ?, 
                Particulars = ?, Amount = ?, "Date Received" = ?
            WHERE JEV = ?
        ''', (payee, obligation_request, accounts_payable, particulars, amount, date_received, jev))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating entry: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/create_account', methods=['POST'])
def create_account():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    try:
        username = request.form['username']
        enduser = request.form['enduser']
        password = request.form['password']
        
        # Hash the password
        hashed_password = generate_password_hash(password)
        
        conn = get_db_connection()
        # Check if username already exists
        existing_user = conn.execute('SELECT id FROM users WHERE username = ?', 
                                   (username,)).fetchone()
        
        if existing_user:
            flash('Username already exists!', 'error')
            return redirect(url_for('accounts'))
        
        # Create new user
        conn.execute('''
            INSERT INTO users (username, enduser, password)
            VALUES (?, ?, ?)
        ''', (username, enduser, hashed_password))
        conn.commit()
        conn.close()
        
        flash('Account created successfully!', 'success')
    except Exception as e:
        flash(f'Error creating account: {str(e)}', 'error')
    
    return redirect(url_for('accounts'))

@app.route('/update_account', methods=['POST'])
def update_account():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    try:
        user_id = request.form['user_id']
        username = request.form['username']
        enduser = request.form['enduser']
        password = request.form['password']
        
        conn = get_db_connection()
        
        # Check if username already exists for different user
        existing_user = conn.execute('''
            SELECT id FROM users 
            WHERE username = ? AND id != ?
        ''', (username, user_id)).fetchone()
        
        if existing_user:
            flash('Username already exists!', 'error')
            return redirect(url_for('accounts'))
        
        if password:  # Update with new password
            hashed_password = generate_password_hash(password)
            conn.execute('''
                UPDATE users 
                SET username = ?, enduser = ?, password = ?
                WHERE id = ?
            ''', (username, enduser, hashed_password, user_id))
        else:  # Update without changing password
            conn.execute('''
                UPDATE users 
                SET username = ?, enduser = ?
                WHERE id = ?
            ''', (username, enduser, user_id))
            
        conn.commit()
        conn.close()
        
        flash('Account updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating account: {str(e)}', 'error')
    
    return redirect(url_for('accounts'))

@app.route('/get_entry/<jev>')
def get_entry(jev):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = get_db_connection()
    entry = conn.execute('SELECT * FROM entry WHERE JEV = ?', (jev,)).fetchone()
    conn.close()
    
    if entry:
        entry_dict = dict(entry)
        # Format dates
        if entry_dict['Date Entry']:
            entry_dict['Date Entry'] = entry_dict['Date Entry'].split()[0]
        if entry_dict['Date Received']:
            entry_dict['Date Received'] = entry_dict['Date Received'].split()[0]
        return jsonify(entry_dict)
    
    return jsonify({'error': 'Entry not found'}), 404

@app.route('/export_data')
def export_data():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    # Get date range parameters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Create an in-memory output file
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()
    
    # Add headers
    headers = ['JEV', 'Payee', 'Obligation Request', 'Accounts Payable', 
              'Particulars', 'Amount', 'Date Entry', 'Date Received']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)
    
    # Build query with date range filter
    query = 'SELECT * FROM entry'
    params = []
    
    if date_from and date_to:
        query += ' WHERE "Date Entry" BETWEEN ? AND ?'
        params.extend([date_from, date_to])
    
    query += ' ORDER BY "Date Entry" DESC'
    
    # Execute query and fetch results
    conn = get_db_connection()
    entries = conn.execute(query, params).fetchall()
    conn.close()
    
    # Define formats
    number_format = workbook.add_format({'num_format': '#,##0.00'})
    date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
    
    # Write data rows
    for row_idx, entry in enumerate(entries, start=1):
        worksheet.write(row_idx, 0, entry['JEV'])
        worksheet.write(row_idx, 1, entry['Payee'])
        worksheet.write(row_idx, 2, entry['ObligationRequest'])
        worksheet.write(row_idx, 3, entry['AccountsPayable'] or '')
        worksheet.write(row_idx, 4, entry['Particulars'])
        worksheet.write_number(row_idx, 5, float(entry['Amount']), number_format)
        
        # Format dates
        for col_idx, date_field in [(6, 'Date Entry'), (7, 'Date Received')]:
            date_value = entry[date_field]
            if date_value:
                try:
                    date_obj = datetime.strptime(date_value.split()[0], '%Y-%m-%d')
                    worksheet.write_datetime(row_idx, col_idx, date_obj, date_format)
                except ValueError:
                    worksheet.write(row_idx, col_idx, date_value)
            else:
                worksheet.write(row_idx, col_idx, '')
    
    # Adjust column widths
    worksheet.set_column('A:A', 15)  # JEV
    worksheet.set_column('B:B', 30)  # Payee
    worksheet.set_column('C:C', 20)  # Obligation Request
    worksheet.set_column('D:D', 20)  # Accounts Payable
    worksheet.set_column('E:E', 40)  # Particulars
    worksheet.set_column('F:F', 15)  # Amount
    worksheet.set_column('G:H', 12)  # Dates
    
    workbook.close()
    output.seek(0)
    
    # Generate filename with date range
    filename = f'database_export_{date_from}_to_{date_to}.xlsx' if date_from and date_to else \
              f'database_export_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/delete_entry/<jev>', methods=['DELETE'])
def delete_entry(jev):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        # Check if entry exists
        entry = conn.execute('SELECT * FROM entry WHERE JEV = ?', (jev,)).fetchone()
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404
            
        # Delete the entry
        conn.execute('DELETE FROM entry WHERE JEV = ?', (jev,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting entry: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/delete_account/<int:user_id>', methods=['DELETE'])
def delete_account(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = get_db_connection()
        
        # Check if user exists
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        # Prevent deleting your own account
        if user_id == session['user_id']:
            return jsonify({'error': 'Cannot delete your own account'}), 400
            
        # Delete the user
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting account: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/search')
def api_search():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    
    # Get filter parameters
    filter_field = request.args.get('field', 'all')
    filter_value = request.args.get('value', '')
    
    # Base query
    query = 'SELECT * FROM entry'
    params = []
    
    # Apply filters if value is provided
    if filter_value:
        if filter_field == 'all':
            query += ''' WHERE (
                JEV LIKE ? OR 
                Payee LIKE ? OR 
                ObligationRequest LIKE ? OR 
                COALESCE(AccountsPayable, '') LIKE ? OR 
                Particulars LIKE ? OR 
                CAST(Amount AS TEXT) LIKE ? OR
                "Date Entry" LIKE ? OR 
                COALESCE("Date Received", '') LIKE ?
            )'''
            search_term = f'%{filter_value}%'
            params.extend([search_term] * 8)
        else:
            # Field-specific search
            if filter_field == 'amount':
                try:
                    amount = float(filter_value)
                    query += ' WHERE Amount = ?'
                    params.append(amount)
                except ValueError:
                    query += ' WHERE CAST(Amount AS TEXT) LIKE ?'
                    params.append(f'%{filter_value}%')
            elif filter_field in ['entryDate', 'receivedDate']:
                field_name = '"Date Entry"' if filter_field == 'entryDate' else '"Date Received"'
                query += f' WHERE {field_name} LIKE ?'
                params.append(f'%{filter_value}%')
            else:
                field_mapping = {
                    'jev': 'JEV',
                    'payee': 'Payee',
                    'obligationRequest': 'ObligationRequest',
                    'accountsPayable': 'AccountsPayable',
                    'particulars': 'Particulars'
                }
                field_name = field_mapping.get(filter_field)
                if field_name:
                    query += f' WHERE {field_name} LIKE ?'
                    params.append(f'%{filter_value}%')
    
    # Add ORDER BY clause
    query += ' ORDER BY "Date Entry" DESC'
    
    # Execute query and format results
    entries = []
    for row in conn.execute(query, params).fetchall():
        entry = dict(row)
        # Format dates
        if entry['Date Entry']:
            try:
                date_entry = datetime.strptime(entry['Date Entry'], '%Y-%m-%d %H:%M:%S')
                entry['Date Entry'] = date_entry.strftime('%Y-%m-%d')
            except ValueError:
                entry['Date Entry'] = entry['Date Entry'].split()[0]
        
        if entry['Date Received']:
            try:
                date_received = datetime.strptime(entry['Date Received'], '%Y-%m-%d %H:%M:%S')
                entry['Date Received'] = date_received.strftime('%Y-%m-%d')
            except ValueError:
                entry['Date Received'] = entry['Date Received'].split()[0]
        
        entries.append(entry)
    
    conn.close()
    return jsonify({'entries': entries})

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000) 