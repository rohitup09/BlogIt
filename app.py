from flask import Flask, render_template, request, redirect, url_for, session
import boto3
import key_config as keys
from flask import jsonify, request
from datetime import datetime


from boto3.dynamodb.conditions import Key, Attr
# ... (previous code)


app = Flask(__name__)
app.secret_key = 'rohit@090'
# Set up DynamoDB resource
dynamodb = boto3.resource('dynamodb',
                    aws_access_key_id=keys.ACCESS_KEY_ID,
                    aws_secret_access_key=keys.ACCESS_SECRET_KEY,
                    aws_session_token=keys.AWS_SESSION_TOKEN,
                    region_name='us-east-1')
table_name = 'BlogPosts'
table = dynamodb.Table(table_name)


def get_posts_sorted_by_likes():
    try:
        response = table.scan(
            IndexName='Likes',  # Replace 'LikesIndex' with the name of your GSI (Global Secondary Index)
            Select='ALL_ATTRIBUTES',  # Retrieve all attributes of the items
            ScanIndexForward=False  # Sort in descending order
        )

        # Extract the items from the response
        posts = response.get('Items', [])

        return posts
    except Exception as e:
        # Handle exceptions based on your application's needs
        print(f"Error fetching posts: {str(e)}")
        return []

def get_post_by_id(post_id):
    try:
        # Use the DynamoDB table's get_item method to retrieve the post by its PostID
        response = table.get_item(
            Key={
                'PostID': post_id
            }
        )

        # If the item is found, return the post data
        if 'Item' in response:
            return response['Item']

    except Exception as e:
        print(f"Error: {e}")

    # If the item is not found or an error occurs, return None
    return None


def encrypt(text, shift):
    result = ""
    for char in text:
        if char.isalpha():
            # Encrypt only alphabetic characters
            start = ord('a') if char.islower() else ord('A')
            result += chr((ord(char) - start + shift) % 26 + start)
        else:
            # Keep non-alphabetic characters unchanged
            result += char
    return result

def decrypt(text, shift):
    # Decryption is the same as encryption with a negative shift
    return encrypt(text, -shift)


@app.route('/')
def index(orderBy='Time',methods=['POST','GET']):
    # Retrieve posts from DynamoDB
    orderBy = request.args.get('orderBy', 'Time')
    response = table.scan()
    posts = response.get('Items', [])
    if request.method=='GET':
        lk=[]
        send=[]
        for post in posts:
            if orderBy=='Likes':
                lk.append(int(post[orderBy]))
            elif orderBy=='Time':
                lk.append(post['Time'])

        lk.sort(reverse=True)

        for i in range(len(lk)):
            for post in posts:
                if post[orderBy]==lk[i]:
                    send.append(post)
    else:
        return render_template('index.html', posts=posts)


    return render_template('index.html', posts=send)

@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        likes = 0
        tags = request.form['tags'].split(',')

        # Add post to DynamoDB
        add_post(title, content,tags)

        return redirect(url_for('index'))

    return render_template('create.html')

def email_exists(mail):
    table1=dynamodb.Table('userdata')
    response = table1.query(
        KeyConditionExpression=Key('email').eq(mail)
    )
    items = response['Items']
    return len(items) > 0

@app.route('/increment_likes/<post_id>', methods=['POST'])
def increment_likes(post_id):
    response = table.update_item(
        Key={'PostID': post_id},
        UpdateExpression='SET Likes = Likes + :val',
        ExpressionAttributeValues={':val': 1},
        ReturnValues='UPDATED_NEW'
    )

    updated_likes = response.get('Attributes', {}).get('Likes', 0)
    return jsonify({'success': True, 'likes': updated_likes})

@app.route('/delete_post/<post_id>', methods=['POST'])
def delete_post(post_id):
    try:
        response = table.delete_item(
            Key={'PostID': post_id},
            ReturnValues='ALL_OLD'
        )

        deleted_post = response.get('Attributes')
        if deleted_post:
            return jsonify({'success': True, 'message': 'Post deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Post not found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        password=encrypt(password,7)
        # Check if an account with the same email already exists
        if email_exists(email):
            # Redirect to an appropriate page (e.g., a page indicating the email is already registered)
            return render_template('login.html')

        table = dynamodb.Table('userdata')

        table.put_item(
                Item={
        'name': name,
        'email': email,
        'password': password
            }
        )
        msg = "Registration Complete. Please Login to your account !"

        return render_template('login.html')
    return render_template('signup.html')

@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/check',methods = ['post'])
def check():
    if request.method=='POST':

        email = request.form['email']
        password1 = request.form['password']
        table = dynamodb.Table('userdata')
        response = table.query(
                KeyConditionExpression=Key('email').eq(email)
        )
        items = response['Items']
        if items:
            if password1 == decrypt(items[0]['password'],7):
                session['email'] = email
                return redirect(url_for('index'))
        return render_template("login.html")
    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/profile')
def profile():
    if 'email' not in session:
        return redirect(url_for('login'))

    user_email = session['email']
    response = table.scan()
    posts = response.get('Items', [])
    pp=[]
    for post in posts:
        if post['Account']==user_email:
            pp.append(post)
    return render_template('profile.html', posts=pp)

@app.route('/edit_post/<post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    # Handle form submission to update post in DynamoDB
    if request.method == 'POST':
        new_content = request.form.get('new_content')
        response = table.scan()
        posts = response.get('Items', [])
        for post in posts:
            if post['PostID']==post_id:
                post['Content']=new_content
                table.put_item(Item=post)


        return redirect(url_for('profile'))

    # Render edit post form
    post = get_post_by_id(post_id)
    return render_template('edit_post.html', post=post)

@app.route('/delete_post/<post_id>')
def delete_post_route(post_id):
    delete_post(post_id)
    return redirect(url_for('profile'))

@app.route('/search')
def search():
    query = request.args.get('query', '')
    # Perform search logic here based on the query (e.g., search in your DynamoDB table)
    # Fetch and filter posts based on the search query
    # For simplicity, let's assume 'posts' is a list of all blog posts

    # Example: Filtering posts containing the query in Title or Content
    response = table.scan()
    posts = response.get('Items', [])
    filtered_posts = [post for post in posts if query.lower() in post['Title'].lower() or query.lower() in post['Content'].lower()]

    return render_template('search_results.html', query=query, posts=filtered_posts)

def add_post(title, content, tags):
    post_id = title.replace(" ", "-").lower()
    now = datetime.now()
    now=str(now)
    #current_time = now.strftime("%H:%M:%S")
    item = {
        'PostID': post_id,
        'Title': title,
        'Content': content,
        'Likes': 0,  # Initial likes count set to 0
        'Tags': tags,
        'Account': session['email'],
        'Time': now
    }

    table.put_item(Item=item)
    print(f"Post '{title}' added to the DynamoDB table.")


if __name__ == '__main__':
    app.run(debug=True,port=7000)
