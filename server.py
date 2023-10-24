from flask import Flask, request, render_template, redirect, flash, session
from flask_session import Session
from atproto import Client, models
import math
import os
import argparse
import re

app = Flask(__name__)
app.config.from_pyfile('config.py')
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_USE_SIGNER"] = "True"
Session(app)

@app.route('/')
def index():
    print('/')
    if not session.get("name"):
        print("Utilisateur non connecté, chargement de la page de connexion")
        return render_template('index.html')
    else:
        print("Déjà connecté, on va sur /thread")
        return redirect('/thread')

@app.route("/login", methods=['GET', 'POST'])
def fctn_login():
    client = Client()

    print ("/login")
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')

        if (connexion(client, login, password) == 0):
            return redirect('/thread')
        else:
            error="Connection error, please check the login and password."
            return render_template("index.html", error=error)

    elif request.method == 'GET':
        if not session.get("name"):
            print("Utilisateur non connecté, redirection vers la page de connexion")
            return redirect('/')
        else:
            print("Déjà connecté, on va sur /thread")
            return redirect('/thread')

    # Just in case
    return redirect('/')

@app.route("/logout", methods=['GET'])
def logout():
    print("- Déconnexion")
    session["name"] = None
    session["password"] = None
    session["profile"] = None
    return redirect('/')


@app.route('/thread',  methods=['GET', 'POST'])
def thread():
    print ('/thread')
    thread=[]
    disabled="disabled='true'"

    if not session.get("name"):
        print("Utilisateur non connecté, redirection vers la page de connexion")
        return redirect("/")

    if request.method == 'POST':
        print ('Entrée avec la méthode POST')

        print("- Envoi du thread")
        # Getting the posts
        thread=request.form.getlist("post")
        # print(thread)
        images=request.files.getlist('input_images')
        #alts=request.form.getlist("alt")
        #print("alts : ", alts)

        if (session.get("profile") is not None):   # If the client has a valid connection to Bluesky
            if (envoi_thread(thread, images, request.form) == 0):
                print("Thread envoyé sur le compte bluesky de " + session.get("name") + " !")
                return render_template('thread_sent.html')
            else :
                print("Erreur lors de l'envoi...")
                flash ("Error when sending the thread...")
        else:
            print("Utilisateur non connecté, envoi impossible")
            flash ("User not logged in, the thread could not be sent. Please log in again.")

    # Affichage de la page thread
    return render_template("thread.html")


@app.errorhandler(404)
def page_not_found(error):
    return ('Page not found :(')


# Connects the client using the login and password
# Input : client, login, password
# Returns 0 if connection ok, else returns 1
def connexion(client, login, password):
    try:
        print("- Connexion...")
        profile = client.login(login, password)
        session["profile"] = profile    # Keeps the infos of the Bluesky profile
        session["name"] = login
        session["password"] = password
    except Exception as error:
        print("Erreur de connexion. Veuillez vérifier l'identifiant et le mot de passe.", type(error).__name__, error)
        session["profile"] = None
        session["name"] = None
        session["password"] = None
        return 1;
    else:
        print("- Connecté en tant que "+session.get("profile").handle)
        return 0;


# Posts the thread on Bluesky
# Input : array of strings, images, form
# Returns 0 if ok
def envoi_thread (thread, images, form):
    premier=True
    str_nb_posts = str(len(thread))
    langue = form.get("lang")
    
    client = Client()
    login=session["name"]
    password=session["password"]
    
    print("- Envoi_thread : ", thread)
    
    if (connexion(client, login, password) == 0):

        for index, post in enumerate(thread):
            numerotation = str(index+1)+"/"+str_nb_posts
            embed=''
            
            try:    # Trying to get an alt for this post
                alt = form.get("alt"+str(index+1))
            except Exception:
                alt = ""  # no alt for this post
                #print("pas de alt récupéré")
            
            if (premier):
                # Sending of the first post, which doesn't reference any post
                # print("image", images[index])
                if (images[index].filename==''):    # If no image
                    #print("pas d'image")
                    root_post_ref = models.create_strong_ref(client.send_post(text=post, langs=[langue]))

                else:   # If there is an image
                    print("Premier post avec une image")
                    img_data=images[index].read()
                    print("Juste avant ''upload_blob''")
                    upload = client.com.atproto.repo.upload_blob(img_data)
                    print("Juste après ''upload_blob''")
                    pics = [models.AppBskyEmbedImages.Image(alt=alt, image=upload.blob)]
                    embed = models.AppBskyEmbedImages.Main(images=pics)
                    
                    root_post_ref = models.create_strong_ref(client.send_post(
                        text=post, langs=[langue], embed=embed
                    ))
                                            
                parent_post_ref = root_post_ref     # The first post ref becomes the ref for the parent post
                premier=False
            else:
                # Sending of another post, replying to the previous one
                if (images[index].filename==''):    # If no image
                    parent_post_ref = models.create_strong_ref(client.send_post(
                        text=post, reply_to=models.AppBskyFeedPost.ReplyRef(parent=parent_post_ref, root=root_post_ref), langs=[langue]
                    ))
                else:   # If there is an image
                    img_data=images[index].read()
                    upload = client.com.atproto.repo.upload_blob(img_data)
                    pics = [models.AppBskyEmbedImages.Image(alt=alt, image=upload.blob)]
                    embed = models.AppBskyEmbedImages.Main(images=pics)
                    
                    parent_post_ref = models.create_strong_ref(client.send_post(
                        text=post, reply_to=models.AppBskyFeedPost.ReplyRef(parent=parent_post_ref, root=root_post_ref), langs=[langue], embed=embed
                    ))
                    
            print("- Post "+numerotation+" envoyé")
            
    else:
        print("Erreur de connexion du client lors de l'envoi...")
        flash ("Connexion error when trying to send...")

    return 0


if __name__ == '__main__':
    app.run(debug=True)