import oracledb
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from app.expense_tracker.connection import get_db_connection
import re
from todoist_api_python.api import TodoistAPI
from datetime import datetime
import pandas as pd

# Create a blueprint
main = Blueprint('main', __name__)

TODOIST_API_URL         = 'https://api.todoist.com/rest/v2/tasks'
TODOIST_API_TOKEN       = 'b0fc1460b2a4f9c4cef8f1b2811452f240c28314'


@main.route('/', methods=['GET', 'POST'])
def login():
    out_message = ""
    status = ""
    message = ""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':

            out_message = cursor.var(oracledb.STRING)
            status = cursor.var(oracledb.STRING)

            username = request.form['username']
            password = request.form['password']
            cursor.callproc('user_login_sp', [out_message, status, username, password])
            cursor.close()
            conn.close()
            out_message_value = out_message.getvalue()
            status_value = status.getvalue()
            if status_value == 'N':
                message = out_message_value
                return render_template('login.html', message=message)
            else:
                return redirect(url_for('main.index'))  # Redirect to the /index endpoint
    except Exception as e:
        print("Error in Login " + str(e))
    return render_template('login.html', message=message)


@main.route('/register', methods=['GET', 'POST'])
def register():
    out_message = ""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            password2 = request.form['password2']

            if not re.match("^[a-zA-Z0-9.@]*$", username):
                out_message = "Invalid username. Only a-z, A-Z, 0-9, '.', and '@' are allowed."
                return render_template('register.html', message=out_message)

            if password == password2:
                register_user_query = """
                insert into et_user_login (user_id, user_name, passwd)
                values
                (et_user_id_seq.nextval, :username, :password)
                """
                cursor.execute(register_user_query, {'username': username, 'password': password})
                conn.commit()
                cursor.close()
                conn.close()
                out_message = f"The Username {username} has been created successfully!"
                return render_template('login.html', message=out_message)
            elif password != password2:
                out_message = "Both the entered passwords are not identical. Please check!"
                return render_template('register.html', message=out_message)

    except Exception as e:
        print("Error in Login " + str(e))
    return render_template('register.html', message=out_message)


# Initialize the Todoist API client
api = TodoistAPI(TODOIST_API_TOKEN)


@main.route('/index', methods=['GET', 'POST'])
def index():
    try:
        print('@1-index')
        conn = get_db_connection()
        cursor = conn.cursor()
        # Fetch category codes for both GET and POST requests
        category_query = """
            SELECT category_code, category_desc
            FROM category_mst
            ORDER BY category_id
        """
        cursor.execute(category_query)
        category_codes = cursor.fetchall()
        print('@2')
        print(request.method)
        if request.method == 'POST':
            # Get form data
            item = request.form['item']
            category = request.form['category']
            price = request.form['price']
            expense_date = request.form['expense_date']
            paid_status = request.form['paid_status']
            reminder_status = request.form.get('button_value')


            if len(expense_date) == 16:  # 'YYYY-MM-DDTHH:MM' format
                expense_date += ':00'

            expense_date = datetime.strptime(expense_date, '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
            # Insert data into the database
            insert_query = """
                INSERT INTO expense_tracker (
                    expense_id, item, category, price, due_paid_ind, created_date, updated_date, expense_date
                ) VALUES (
                    expense_tracker_exp_id_seq.NEXTVAL, :item, :category, :price, :paid_status,
                    SYSDATE + (330 / 1440), SYSDATE + (330 / 1440), to_date(:expense_date,'yyyy-mm-dd hh24:mi:ss')
                )
            """
            cursor.execute(insert_query,
                           {'item': item, 'category': category, 'price': price, 'paid_status': paid_status, 'expense_date': expense_date})
            conn.commit()

            # Success message
            success_message = f"Save the details for {item} for the price {price} ."
            cursor.close()
            conn.close()
            print('the value will be: '+reminder_status)
            if reminder_status =='R':
                print('the value will be R')
                create_todoist_task(item, category, price, expense_date)
            return render_template('success.html', success_message=success_message)

        # Close the connection
        cursor.close()
        conn.close()

        # Render the index page with expenses and pagination info
        return render_template(
            'index.html',
            title='Expense Tracker',
            category_codes=category_codes
        )

    except Exception as e:
        print(f"Error encountered: {str(e)}")
        return render_template('success.html', success_message="An error occurred while processing your request.")




def create_todoist_task(item, category, price, expense_date):
    try:


        expense_date_str = str(expense_date)
            # If it's a single string, parse and format it
        date_str = datetime.strptime(expense_date_str, "%Y-%m-%d %H:%M:%S")
        due_date = date_str.strftime("%Y-%m-%dT%H:%M:%S")  # Keep it in local time
        # Create the task in Todoist
        task = api.add_task(
            content=f"Payment for {item} ({category}) - ₹{price}",
            due_string=due_date,  # You can use due_string for a simple due date
            priority=4,  # Priority level (1-4)
            )

        # Success message
        print(task)

    except Exception as error:
        # Error handling
        print(f"Failed to create task for {item}: {error}")






@main.route('/view_expense', methods=['GET','POST'])
def view_expense():
    page = request.args.get('page', default=1, type=int)  # Get the page number from the URL, default to 1
    records_per_page = 10  # Number of records per page
    offset = (page - 1) * records_per_page  # Calculate the offset
    export_param=""
    message=""
    try:

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM expense_tracker")
        total_records = cursor.fetchone()[0]
        total_pages = (total_records + records_per_page - 1) // records_per_page  # Calculate total pages
        # Fetch search parameters
        from_expense_date_search = request.args.get('from_expense_date_search', None)
        to_expense_date_search = request.args.get('to_expense_date_search', None)
        due_paid_ind_search = request.args.get('due_paid_ind_search',  None)  # Default to 'A' (All)
        export_param = request.args.get('export_param',None)
        print(records_per_page, offset)
        print("the value of dpi is")
        print(from_expense_date_search,to_expense_date_search)

        params = {}

        # Define the query
        query = """      
            SELECT expense_id, item, category_code, category, price, due_paid_ind, 
                   TO_CHAR(updated_date, 'dd-Mon-yyyy HH24:MI:SS') updated_date, 
                   TO_CHAR(expense_date, 'dd-Mon-yyyy hh24:mi:ss') expense_date
            FROM (
                SELECT et.expense_id, et.item, cm.category_code, cm.category_desc category, et.price,
                       DECODE(et.due_paid_ind, 'D', 'Due to Pay', 'P', 'Paid', 'R', 'Received', ' ') due_paid_ind,
                       et.updated_date,
                       ROW_NUMBER() OVER (ORDER BY et.updated_date DESC) AS rn, et.expense_date
                FROM expense_tracker et, category_mst cm
                WHERE et.category = cm.category_code
                AND  (:from_expense_date_search IS NULL OR expense_date >= to_date(:from_expense_date_search,'yyyy-mm-dd'))
                  AND (:to_expense_date_search IS NULL OR expense_date <= to_date(:to_expense_date_search,'yyyy-mm-dd'))
                  AND (:due_paid_ind_search IS NULL OR et.due_paid_ind = :due_paid_ind_search)
            )
            WHERE rn BETWEEN :offset + 1 AND :offset + :limit
            group by expense_id, item, category_code, category, price, due_paid_ind, updated_date, expense_date
            ORDER by expense_id desc
        """

        # Add optional filters
        # Set `None` for empty values or 'A' for due_paid_ind_search
        if not from_expense_date_search:
            from_expense_date_search = None

        if not to_expense_date_search:
            to_expense_date_search = None

        if due_paid_ind_search == 'A' or not due_paid_ind_search:
            due_paid_ind_search = None

        # Define parameters
        params = {
            'from_expense_date_search': from_expense_date_search,
            'to_expense_date_search': to_expense_date_search,
            'due_paid_ind_search': due_paid_ind_search,
            'offset': offset,
            'limit': records_per_page
        }

        # Execute the query
        try:
            cursor.execute(query, params)
            expenses = cursor.fetchall()
            print("Expenses fetched successfully.")
        except Exception as e:
            print(f"Error fetching expenses: {e}")

        if expenses:
            sum_expense = sum(row[4] for row in expenses)
        else:
            sum_expense = 0
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        print("the value of export_param")
        print(export_param)
        if export_param == 'E':
            df = pd.read_sql(query, con=conn, params=params)

            # Add the total sum row to the DataFrame
            blank_row = pd.DataFrame([['', '', '', '', '', '', '', '']], columns=df.columns)
            total_row = pd.DataFrame([['', '', 'Total Sum (Price):', '', sum_expense, '', '', '']], columns=df.columns)
            df = pd.concat([df,blank_row,blank_row, total_row], ignore_index=True)
            output_file = f'expenses_{timestamp}.xlsx'
            df.to_excel(output_file, index=False)
            message=f"Data successfully exported to {output_file}"

        cursor.close()
        conn.close()
        return render_template(
            'view_expense.html',
            expenses=expenses,
            page=page,
            total_pages=total_pages,
            sum_expense=sum_expense,
            message=message
        )
    except Exception as e:
        return f"Error fetching expenses: {str(e)}"




@main.route('/edit_expense', methods=['GET', 'POST'])
def edit_expense():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            # Collect selected IDs
            selected_ids = request.form.getlist('selected_ids')
            if not selected_ids:
                return jsonify({"error": "No expenses selected for update."})
            action = request.form['action']
            selected_ids = list(map(int, selected_ids))
            # Iterate and update each selected expense
            print("the value for action in edit expense is: " + action)
            success_message = []
            if action == 'U':
                for expense_id in selected_ids:
                    item = request.form.get(f'item_{expense_id}')
                    category = request.form.get(f'category_{expense_id}')
                    price = request.form.get(f'price_{expense_id}')
                    expense_date = request.form.get(f'expense_date_{expense_id}')

                    if len(expense_date) == 16:  # 'YYYY-MM-DDTHH:MM' format
                        expense_date += ':00'

                    expense_date = datetime.strptime(expense_date, '%Y-%m-%dT%H:%M:%S').strftime('%Y-%m-%d %H:%M:%S')
                    print(expense_date)
                    update_query = """
                    UPDATE expense_tracker
                    SET item = :item, category = :category, price = :price, updated_date = SYSDATE, expense_date = to_date(:expense_date, 'yyyy-mm-dd hh24:mi:ss')
                    WHERE expense_id = :expense_id
                    """
                    cursor.execute(update_query,
                                   {'item': item, 'category': category, 'price': price, 'expense_id': expense_id,
                                    'expense_date': expense_date})
                success_message = "Updated the selected record(s) successfully!!"
            elif action == 'D':
                delete_expense_query = """
                                DECLARE
                                    TYPE exp_id_tab_type IS TABLE OF expense_tracker.expense_id%TYPE;
                                    exp_id_tab exp_id_tab_type;
                                BEGIN
                                    -- Populate the nested table
                                    exp_id_tab := exp_id_tab_type();
                                    FOR i IN 1..:num_ids LOOP
                                        exp_id_tab.EXTEND;
                                        exp_id_tab(i) := :id_list(i);
                                    END LOOP;

                                    -- Perform bulk delete
                                    FORALL i IN 1..exp_id_tab.COUNT
                                        DELETE FROM expense_tracker
                                        WHERE expense_id = exp_id_tab(i);
                                END;
                                """
                # Bind the list of integers and its length to the query
                cursor.execute(delete_expense_query, {
                    'id_list': selected_ids,
                    'num_ids': len(selected_ids)
                })
                success_message = "Deleted the selected record(s) successfully!!"
            # Commit changes to the database
            conn.commit()
            # Handle GET request: Fetch all expenses for viewing
            fetch_query = """
            SELECT expense_id, item, cm.category_code cat_cd , cm.category_desc category, price, decode(et.due_paid_ind, 'D' ,'Due to Pay', 'P' , 'Paid', 
            'R', 'Received', ' ') due_paid_ind, 
            et.created_date created_date,to_char(expense_date,'yyyy-mm-dd hh24:mi:ss') expense_date
            FROM expense_tracker et, category_mst cm
            where et.category=cm.category_code
            ORDER BY expense_id DESC
            """
            cursor.execute(fetch_query)
            expenses = cursor.fetchall()  # Fetch all records from the query
            cursor.close()
            conn.close()
            return render_template('edit_expense.html', expenses=expenses, message=success_message)

        # Handle GET request: Fetch all expenses for viewing
        fetch_query = """
        SELECT expense_id, item, cm.category_code cat_cd , cm.category_desc category, price, decode(et.due_paid_ind, 'D' ,'Due to Pay', 'P' , 'Paid', 
            'R', 'Received', ' ') due_paid_ind, 
        et.created_date created_date,to_char(expense_date,'yyyy-mm-dd hh24:mi:ss') expense_date
        FROM expense_tracker et, category_mst cm
        where et.category=cm.category_code
        ORDER BY expense_id DESC
        """
        cursor.execute(fetch_query)
        expenses = cursor.fetchall()  # Fetch all records from the query
        cursor.close()
        conn.close()

        # Render template for editing expenses
        return render_template('edit_expense.html', expenses=expenses)

    except Exception as e:
        return jsonify({"error": str(e)})


@main.route('/create_category', methods=['GET', 'POST'])
def create_category():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            category_code = request.form['category_code']
            category_desc = request.form['category_desc']
            insert_cat_query = """
            insert into category_mst (category_id, category_code, category_desc, created_date, updated_date)     
            VALUES
            (cat_seq.nextval, :category_code, :category_desc, sysdate, sysdate)
            """
            cursor.execute(insert_cat_query, {'category_code': category_code, 'category_desc': category_desc})
            conn.commit()

        view_cat_query = """
                   select category_id, category_code, category_desc, created_date, updated_date     
                   from category_mst
                   order by category_id
                   """
        cursor.execute(view_cat_query)
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('create_category.html', categories=categories)
    except Exception as e:
        return jsonify({"error": str(e)})


@main.route('/edit_category', methods=['GET', 'POST'])
def edit_category():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        categories = []

        if request.method == 'POST':

            selected_ids = request.form.getlist('selected_ids')

            if not selected_ids:
                return jsonify({"error": "No category selected for update."})

            action = request.form['action']
            print("the actions in edit_category: " + action)

            selected_ids = list(map(int, selected_ids))
            if action == 'U':
                for category_id in selected_ids:
                    category_code = request.form.get(f'category_code_{category_id}')
                    category_desc = request.form.get(f'category_desc_{category_id}')

                    update_cat_query = """
                    update category_mst 
                    set  category_code = :category_code, 
                         category_desc = :category_desc, 
                         created_date = sysdate, 
                         updated_date = sysdate
                    where category_id =:category_id
                    """
                    cursor.execute(update_cat_query, {'category_id': category_id, 'category_code': category_code, 'category_desc': category_desc})

            elif action == 'D':
                delete_category_query = """
                DECLARE
                    TYPE cat_id_tab_type IS TABLE OF category_mst.category_id%TYPE;
                    cat_id_tab cat_id_tab_type;
                BEGIN
                    -- Populate the nested table
                    cat_id_tab := cat_id_tab_type();
                    FOR i IN 1..:num_ids LOOP
                        cat_id_tab.EXTEND;
                        cat_id_tab(i) := :id_list(i);
                    END LOOP;
    
                    -- Perform bulk delete
                    FORALL i IN 1..cat_id_tab.COUNT
                        DELETE FROM category_mst
                        WHERE category_id = cat_id_tab(i);
                END;
                """
                # Bind the list of integers and its length to the query
                cursor.execute(delete_category_query, {
                    'id_list': selected_ids,
                    'num_ids': len(selected_ids)
                })
                success_message = "Deleted the requested records successfully!!"
            conn.commit()
            view_cat_query = """
                               select category_id, category_code, category_desc     
                               from category_mst
                               order by category_id
                               """
            cursor.execute(view_cat_query)
            categories = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('edit_category.html', categories=categories)

        view_cat_query = """
                           select category_id, category_code, category_desc     
                           from category_mst
                           order by category_id
                           """
        cursor.execute(view_cat_query)
        categories = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('edit_category.html', categories=categories)
    except Exception as e:
        return jsonify({"error": str(e)})




