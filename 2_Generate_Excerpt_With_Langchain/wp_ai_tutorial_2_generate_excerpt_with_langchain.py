
# Load Packages
import pymysql
import pandas as pd
import os
import re
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic


def connect_mysql():
    '''
    Connect to MySQL
    '''
    conn = pymysql.connect(
        host='your_host',
        user='your_user',
        password='your_password',
        database='your_database',
        port=3306,
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()
    return conn, cursor


def get_posts_with_lang():
    '''
    Get posts with language code
    '''
    sql = '''
    SELECT *
    FROM wp_posts
    WHERE post_type = 'post'
    AND post_status = 'publish'
    ORDER BY post_date DESC
    '''

    conn, cursor = connect_mysql()
    cursor.execute(sql)
    list_cursor = list(cursor)
    result = pd.DataFrame(list_cursor)
    conn.close()
    return result


def update_excerpt_and_log(row, summary):
    '''
    Update the excerpt of the post
    '''
    sql = f"""
    UPDATE wp_posts 
    SET post_excerpt = '{summary}'
    WHERE ID = {int(row['ID'])}
    AND post_type = 'post';
    """
    conn, cursor = connect_mysql()
    cursor.execute(sql)
    conn.commit()
    conn.close()


def summarize_post(row):
    '''
    Summarize the post in English
    '''
    model = ChatAnthropic(model="claude-3-5-sonnet-20240620",
                          temperature=0.2, max_tokens=200,
                          anthropic_api_key=os.environ["ANTHROPIC_API_KEY"])

    prompt_template = """
    Please mimic the writing style of the article and create a concise summary in English, keeping it under 50 words. 
    Provide only the summary content without any explanations.
    Imagine you are the author and avoid starting with:
    - "This article..."
    - "In this post..."
    - "We discuss..."
    - "Let me introduce..."

    Here is the article content:
    {content}

    Assistant: """

    # Clean the content
    strip_content = row['post_content'].strip()
    strip_content = re.sub(r'<[^>]*>', '', strip_content)

    # Skip if the content is too short
    if len(strip_content) < 100:
        print(f'{row["post_title"]} is too short')
        return

    message = HumanMessage(content=prompt_template.format(
        content=strip_content))
    response = model.invoke([message])
    summary = response.content
    summary = summary.replace(',', '，')
    return summary


def main():
    '''
    Main function
    '''
    os.environ["ANTHROPIC_API_KEY"] = 'your_anthropic_api_key'
    wp_posts = get_posts_with_lang()

    for i in range(len(wp_posts)):
        row = wp_posts.iloc[i]
        summary = summarize_post(row=row)
        if summary is None:
            continue

        print(f'{summary}')
        try:
            update_excerpt_and_log(row=row, summary=summary)
        except Exception as e:
            print(e)
        print(f'{i} / {len(wp_posts)}')


if __name__ == '__main__':
    main()
