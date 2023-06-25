# simple_comment_bot_Telegram
This document is a set of commands for controlling the bot in the Telegram chat. All commands assume a certain level of access (usually administrator). Replace YOUR_ID with your Telegram id and Your Bot Token with your bot's token. Then add the bot to your chat and make it an administrator.

# Telegram bot control commands

## /start
Initializes the bot and greets you.

## /create_post
Creates a new post. Available to administrators only. The bot will ask you to enter the text of the post, then an image to be attached to the post. Once the post is successfully created, a message will be sent to you with the ID of the created post.

## /publish_post.
Publishes the post. Only available to administrators. You must specify the post ID and the topic (post) ID where the post text will be sent as a reply.
Example usage: `/publish_post <post ID> <topic ID>

## /delete_post
Deletes the post. Only available to administrators. You must specify the post ID you want to delete.
Example usage: `/delete_post <postID>`

## /view_posts
View a list of all posts. This command shows a list of all posts with their ID and publication status.

## /edit_post
Edit post. Available to administrators only. You must specify the ID of the post you want to edit. Then enter new text for the post.
Example usage: `/edit_post <post ID>

## /comment
Add a comment to the post. You must specify the post ID you want to add a comment to, and then write the comment text.
Example usage: `/comment <post ID> <comment text>

## /view_comments
View comments on the post. You must specify the ID of the post whose comments you want to view.
Example usage: `/view_comments <ID of post>`

Note:
The `<ID of post>` and `<ID of topic>` must be integers without angle brackets.
The `<comment text>` can contain any text you want to add to the comment.
