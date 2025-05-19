import oracledb
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for

from .connection import get_db_connection
from collections import defaultdict


main = Blueprint('fb_main', __name__)

@main.route('/fb_home', methods=['GET', 'POST'])
def fb_home():
    conn = get_db_connection()
    cursor = conn.cursor()

    meal_type = request.form.get('meal-type')
    print('gautam meal type', meal_type)
    form_submit = request.form.get('form-submitted')
    get_details = request.form.get('get_details') # Check if it's a request for food details
    food_items = []
    print("initial form_submit:", form_submit)
    if not form_submit:
        form_submit = '0'

    # Handle search suggestions (GET request with 'q' param)
    query = request.args.get('q', '').strip().lower()
    if query:
        cursor.execute("""
            SELECT DISTINCT FOOD FROM FOOD_ITEMS
            WHERE LOWER(FOOD) LIKE :query
        """, {'query': f"%{query}%"})
        suggestions = [row[0] for row in cursor.fetchall()]
        conn.close()
        print('@@@1 suggestions:', suggestions)
        return jsonify(suggestions)
    print('@@@2')
    # Handle normal form submission
    suggestions = []
    food_name = request.form.get('food-name', '')
    calories = request.form.get('calories', '')
    unit = request.form.get('unit', '')
    quantity = float(request.form.get('quantity', 1)) if request.form.get('quantity') else 1

    # Handle request for food details
    if request.method == 'POST' and get_details == '1' and food_name:
        cursor.execute("""
            SELECT CALORIES, UNIT FROM FOOD_ITEMS
            WHERE FOOD = :food
        """, {'food': food_name})
        row = cursor.fetchone()
        conn.close()
        if row:
            return jsonify({'calories': row[0], 'unit': row[1]})
        return jsonify({})

    if request.method == 'POST' and form_submit == '1' and meal_type and food_name and calories and unit:
        print("coming hereeeeeee, form_submit:", form_submit, "meal_type:", meal_type)
        cursor.execute("""
            INSERT INTO USER_FOOD_LOG (MEAL_TYPE, FOOD, CALORIES, QUANTITY, UNIT, LOGGED_AT)
            VALUES (:meal_type, :food, :calories, :quantity, :unit, SYSDATE+(5.5/24))
        """, {
            'meal_type': meal_type,
            'food': food_name,
            'calories': calories,
            'quantity': quantity,
            'unit': unit
        })
        conn.commit()
        conn.close()
        return redirect(url_for('fb_main.fb_home'))

    # Fetch all food entries to display in the table (GET request)
    print("get 1")
    cursor.execute("""
        SELECT ID,
            MEAL_TYPE,
            FOOD,
            CALORIES,
            QUANTITY,
            UNIT,
            SUM(CALORIES) OVER (PARTITION BY MEAL_TYPE) AS  SUM_MEAL_TYPE,
            SUM(CALORIES) OVER () AS SUM_CALORIES
        FROM
            USER_FOOD_LOG
        WHERE
                LOGGED_AT >= TRUNC(SYSDATE)
            AND LOGGED_AT <= SYSDATE+(5.5/24)
        ORDER BY
            CASE
                WHEN MEAL_TYPE = 'Breakfast'     THEN 1
                WHEN MEAL_TYPE = 'Morning Snack' THEN 2
                WHEN MEAL_TYPE = 'Lunch'         THEN 3
                WHEN MEAL_TYPE = 'Evening Snack' THEN 4
                WHEN MEAL_TYPE = 'Dinner'        THEN 5
                ELSE 6
            END,
            LOGGED_AT ASC
    """)
    food_items = [
        {
            'id': row[0],
            'meal_type': row[1],
            'food_name': row[2],
            'calories': row[3],
            'quantity': row[4],
            'unit': row[5],
            'sum_meal_type': row[6],
            'sum_all_meals': row[7]
        }
        for row in cursor.fetchall()
    ]
    print("get 2")
    conn.close()
    if food_items:
        print("food items not null", food_items[-1])
    print("get 3")

    # Grouping items by meal type
    grouped_items = defaultdict(list)
    meal_totals = {}
    total_calories = 0

    for item in food_items:
        grouped_items[item['meal_type']].append(item)
        meal_totals[item['meal_type']] = item['sum_meal_type']  # same value for all rows in group
        total_calories = item['sum_all_meals']  # same for all rows
    return render_template('fb_home.html',
                           suggestions=suggestions,
                           food_name=food_name,
                           calories=calories,
                           unit=unit,
                           quantity=quantity,
                           food_items=food_items,
                           form_submit=form_submit,
                           grouped_items=grouped_items,
                           meal_totals=meal_totals,
                           total_calories=total_calories)






@main.route('/fb_add_food', methods=['GET', 'POST'])
def fb_add_food():
    conn = get_db_connection()
    cursor = conn.cursor()
    food_name = request.form.get('food-name', "")
    calories = request.form.get('calories', 0)
    unit = request.form.get('unit', 1)
    if food_name:
        cursor.execute("""
            SELECT CALORIES, UNIT FROM FOOD_ITEMS
            WHERE FOOD = :food
        """, {'food': food_name})
        row = cursor.fetchone()
        if row:
            calories, unit = row

    if request.method == 'POST':
        form_submitted = request.form.get('form-submitted')
        check_food_click = request.form.get('check-food-click')
        print('form_submitted123', form_submitted, '-', check_food_click)
        if check_food_click == '1':
            status_var = cursor.var(str)
            cursor.callproc('et_sp_check_food', [food_name, status_var])
            status = status_var.getvalue()
            print(f"Status: {status}")
            if status == 'Y':
                flash("The Food Items already exists!", "error_top")
                return render_template('fb_add_food.html')
            else:
                flash("The Food Items does not exists. You can proceed to enter it in Database", "error_top")
                return render_template('fb_add_food.html', food_name=food_name)
        else:
            status = 'N'
        if form_submitted == '1':
            try:
                if status == 'N':
                    cursor.execute(
                        """
                        insert into food_items (food,calories,unit)
                        values (:food_name,:calories,:unit)
                        """,
                        {'food_name': food_name,
                         'calories': calories,
                         'unit': unit
                         }
                    )
                    cursor.close()
                    conn.commit()
                    flash("The Food Items has been added to the Database", "error_bottom")
                    return render_template('fb_add_food.html')

            except Exception as e:
                flash("Error while inserting food into DB", "error_bottom")
                print(f"Error while inserting food into DB: {e}")
    return render_template('fb_add_food.html', food_name=food_name, calories=calories, unit=unit)


@main.route('/delete/<int:food_id>', methods=['POST'])
def delete_food(food_id):
    # Delete the record from DB
    conn = get_db_connection()
    cursor = conn.cursor()

    delete_query = "DELETE FROM user_food_log WHERE id = :1"
    cursor.execute(delete_query, [food_id])
    conn.commit()
    flash('Food item deleted!', 'message')
    return redirect(url_for('fb_main.fb_home'))


@main.route('/delete_all', methods=['POST'])
def delete_all(food_id):
    # Delete the record from DB
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the Oracle collection type
    t_number_type = conn.gettype("T_NUMBER")  # Make sure T_NUMBER is correct case

    # Create the collection object and populate it
    id_list = [101, 102, 103]  # Example IDs you want to delete
    collection = t_number_type.newobject()
    for id_value in id_list:
        collection.append(id_value)

    # Prepare an output variable for the message
    p_message = cursor.var(str)

    # Call the stored procedure
    cursor.callproc("FB_SP_DELETE_ALL_FOOD_TXN", [collection, p_message])

    # Print the output message
    print("Procedure Output:", p_message.getvalue())

    conn.commit()
    flash('Food item deleted!', 'message')
    return redirect(url_for('fb_main.fb_home'))


@main.route('/modify/<int:food_id>', methods=['GET', 'POST'])
def modify_food(food_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        meal_type = request.form.get('meal_type', "")
        quantity = request.form.get('quantity', 1)
        print("gautam mt, qt", meal_type, quantity)

        # Ensure we're not getting None values
        if meal_type is None or quantity is None:
            flash('Meal type and quantity cannot be empty!', 'error_bottom')
            return redirect(url_for('fb_main.fb_home'))

        # Convert quantity to float for calculation
        try:
            quantity = float(quantity)
        except ValueError:
            flash('Quantity must be a number!', 'error_bottom')
            return redirect(url_for('fb_main.fb_home'))

        select_qry="select meal_type,quantity, food from user_food_log where id = :1"
        cursor.execute (select_qry, [food_id])
        existing = cursor.fetchone()
        existing_meal_type = str(existing[0])
        existing_quantity = float(existing[1])
        existing_food = str(existing[2])
        if not existing_quantity or not existing_meal_type:
            flash('Quantity or Meal type does not exist for the id!', 'message')

        if (existing_quantity != quantity) or (existing_meal_type != meal_type):
            select_food_items = "select calories from food_items where lower(food)=lower(:1)"
            cursor.execute(select_food_items,[existing_food])

            existing_food_calories = cursor.fetchone()
            existing_food_calories_f=existing_food_calories[0]
            # Updated query - note we're only using two placeholders now
            update_query = """
                        UPDATE user_food_log
                        SET meal_type = :1, quantity = :2, calories = case when quantity != :3 then
                                                                       round(:4 * :5) else
                                                                       calories end 
                        WHERE id = :6
                    """

            # Execute update with proper parameters
            cursor.execute(update_query, (meal_type, quantity, quantity, existing_food_calories_f, quantity, food_id))
            conn.commit()
            flash('Food item updated!', 'message')

        return redirect(url_for('fb_main.fb_home'))

    # GET request: Fetch record
    cursor.execute("SELECT * FROM user_food_log WHERE id = :1", (food_id,))
    food_item = cursor.fetchone()

    if not food_item:
        flash('Food item not found!', 'error_bottom')
        return redirect(url_for('fb_main.fb_home'))

    return render_template('fb_home.html', food_item=food_item)
