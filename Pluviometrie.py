import http.server
import socketserver
from urllib.parse import urlparse, parse_qs, unquote
import json

import matplotlib.pyplot as plt
import datetime as dt
import matplotlib.dates as pltd

import sqlite3

#
# Définition du nouveau handler
#
class RequestHandler(http.server.SimpleHTTPRequestHandler):

  # sous-répertoire racine des documents statiques
  static_dir = '/client'

  #
  # On surcharge la méthode qui traite les requêtes GET
  #
  def do_GET(self):

    # On récupère les étapes du chemin d'accès
    self.init_params()

    # le chemin d'accès commence par /stations
    if self.path_info[0] == 'stations':
      self.send_stations()
      
    # le chemin d'accès commence par /pluvio
    elif self.path_info[0] == 'pluvio':
      self.send_pluvio()
      
    # le chemin d'accès commence par /compare
    elif self.path_info[0] == 'compare':
      self.send_pluvio(compare=True)

    # ou pas...
    else:
      self.send_static()

  #
  # On surcharge la méthode qui traite les requêtes HEAD
  #
  def do_HEAD(self):
    self.send_static()

  #
  # On envoie le document statique demandé
  #
  def send_static(self):

    # on modifie le chemin d'accès en insérant un répertoire préfixe
    self.path = self.static_dir + self.path

    # on appelle la méthode parent (do_GET ou do_HEAD)
    # à partir du verbe HTTP (GET ou HEAD)
    if (self.command=='HEAD'):
        http.server.SimpleHTTPRequestHandler.do_HEAD(self)
    else:
        http.server.SimpleHTTPRequestHandler.do_GET(self)
  
  #     
  # on analyse la requête pour initialiser nos paramètres
  #
  def init_params(self):
    # analyse de l'adresse
    info = urlparse(self.path)
    self.path_info = [unquote(v) for v in info.path.split('/')[1:]]  # info.path.split('/')[1:]
    self.query_string = info.query
    self.params = parse_qs(info.query)

    # récupération du corps
    length = self.headers.get('Content-Length')
    ctype = self.headers.get('Content-Type')
    if length:
      self.body = str(self.rfile.read(int(length)),'utf-8')
      if ctype == 'application/x-www-form-urlencoded' : 
        self.params = parse_qs(self.body)
    else:
      self.body = ''
   
    # traces
    print('info_path =',self.path_info)
    print('body =',length,ctype,self.body)
    print('params =', self.params)
    
  #
  # On génère et on renvoie la liste des stations et leur coordonnées (version TD3)
  #
  def send_stations(self):

    conn = sqlite3.connect('pluvio.sqlite')
    c = conn.cursor()
    
    c.execute("SELECT * FROM 'stations-pluvio-2018'")
    r = c.fetchall()
    
    headers = [('Content-Type','application/json')]
    #body = json.dumps([{'X':X, 'Y':Y, 'Z': Z, 'nom':nom, 'adresse':adresse,'proprietai':proprietai,'datemisens':datemisens,'datemishor':datemishor,'zsol':zsol,'appartenan':appartenan, 'identifian':identifian, 'gid':gid} for (X,Y,Z,nom,adresse,proprietai,datemisens,datemishor,zsol,appartenan,identifian,gid) in r])
    body = json.dumps([{'nom':nom, 'long':X, 'lat':Y} for (X,Y,Z,nom,adresse,proprietai,datemisens,datemishor,zsol,appartenan,identifian,gid) in r])
    self.send(body,headers)

  #
  # On génère et on renvoie un graphique de l'historique des pluies (cf. TD1)
  #
  def send_pluvio(self,compare=False):
    station = self.path_info[1]
    if compare:
        station2 = self.path_info[2]
        d=1
    else:
        station2 = ""
        d=0
    
    # recuperation des dates de debut et de fin
    if len(self.path_info)>3+d:
        debut = int(self.path_info[2+d])
        fin = int(self.path_info[3+d])
    else:
        debut = 2011
        fin = 2018

    conn = sqlite3.connect('pluvio.sqlite')
    c = conn.cursor()
    
    # On verifie que la station demandée existe bien
    c.execute("SELECT identifian FROM 'stations-pluvio-2018' WHERE nom=?", (station,))
    reg = c.fetchall()
    if len(reg)==0:
        print ('Erreur nom')
        self.send_error(404)    # Station non trouvée -> erreur 404
        return None
    else:
        sid = int(reg[0][0]) # identifiant de la station

    if compare:
        # Si on compare deux stations on fait de même avec la 2e
        c.execute("SELECT identifian FROM 'stations-pluvio-2018' WHERE nom=?", (station2,))
        reg = c.fetchall()
        if len(reg)==0:
            print ('Erreur nom')
            self.send_error(404)    # Station non trouvée -> erreur 404
            return None
        else:
            sid2 = int(reg[0][0]) # identifiant de la station
    
    # On recherche les données dans le cache
    c.execute("SELECT Fichier FROM 'Cache' WHERE Station=? AND Station2=? AND Debut=? AND Fin=?", (self.path_info[1],station2, debut,fin))
    fichier = c.fetchall()
    if len(fichier)==0: 
        # configuration du tracé
        fig1 = plt.figure(figsize=(18,9))
        ax = fig1.add_subplot(111)
        ax.set_ylim(bottom=0,top=250)
        ax.grid(which='major', color='#888888', linestyle='-')
        ax.grid(which='minor',axis='x', color='#888888', linestyle=':')
        if fin==debut:
            ax.xaxis.set_major_locator(pltd.MonthLocator())
        elif fin-debut==1:
            ax.xaxis.set_major_locator(pltd.MonthLocator(range(1,13,2)))
        elif fin-debut==2:
            ax.xaxis.set_major_locator(pltd.MonthLocator(range(1,13,3)))
        elif fin-debut==3:
            ax.xaxis.set_major_locator(pltd.MonthLocator(range(1,13,4)))
        elif fin-debut<=5:
            ax.xaxis.set_major_locator(pltd.MonthLocator(range(1,13,6)))
        else:
            ax.xaxis.set_major_locator(pltd.YearLocator())
        ax.xaxis.set_minor_locator(pltd.MonthLocator())
        ax.xaxis.set_major_formatter(pltd.DateFormatter('%B %Y'))
        ax.xaxis.set_tick_params(labelsize=10)
        ax.xaxis.set_label_text("Date")
        ax.yaxis.set_label_text("Hauteur de pluie mesurée (en mm)")
                
        sta = "sta-"+str(sid) 
        # recupération de la date (mois-annee) et de la hauteur pour cette date
        c.execute("SELECT SUBSTR(date,4,7) AS mois,SUM(`"+sta+"`) FROM 'pluvio-histo-2018' WHERE `"+sta+"_e`!='*' GROUP BY mois")
        r = c.fetchall()
        # recupération de la date (colonne 1) et transformation dans le format de pyplot
        x = [pltd.date2num(dt.date(int(a[0][3:7]),int(a[0][:2]),1)) for a in r if int(a[0][3:7])>=debut and int(a[0][3:7])<=fin]
        # récupération de la hauteur (colonne 2)
        y = [ ( 0.0 if a[1]=='' else float(a[1]) ) for a in r if int(a[0][3:7])>=debut and int(a[0][3:7])<=fin]
        # trie selon date
        x,y = zip(*sorted(zip(x, y)))
        # tracé de la courbe
        plt.plot(x,y,linewidth=1, linestyle='-', marker='o', color='blue', label=station)

        if compare:
            # idem pour la 2e station
            sta2 = "sta-"+str(sid2) 
            c.execute("SELECT SUBSTR(date,4,7) AS mois,SUM(`"+sta2+"`) FROM 'pluvio-histo-2018' WHERE `"+sta2+"_e`!='*' GROUP BY mois")
            r = c.fetchall()
            x2 = [pltd.date2num(dt.date(int(a[0][3:7]),int(a[0][:2]),1)) for a in r if int(a[0][3:7])>=debut and int(a[0][3:7])<=fin]
            y2 = [ ( 0.0 if a[1]=='' else float(a[1]) ) for a in r if int(a[0][3:7])>=debut and int(a[0][3:7])<=fin]
            x2,y2 = zip(*sorted(zip(x2, y2)))
            plt.plot(x2,y2,linewidth=1, linestyle='-', marker='o', color='red', label=station2)
            
        # légendes
        plt.legend(loc='lower left')
        if compare:
            plt.title('Pluviométrie '+station+" - "+station2,fontsize=16)
            fichier = 'courbes/pluvio_'+station+'_'+station2+'_'+str(debut)+'_'+str(fin)+'.png'
        else:
            plt.title('Pluviométrie '+station,fontsize=16)
            fichier = 'courbes/pluvio_'+station+'_'+str(debut)+'_'+str(fin)+'.png'

        # génération des courbes dans un fichier PNG
        plt.savefig('client/{}'.format(fichier))
        plt.close()
        
        data = {"Station" : station, "Station2": station2, "Debut" : debut, "Fin" : fin, "Fichier" : fichier}
        c.execute("""INSERT INTO Cache (Station, Station2, Debut, Fin, Fichier) VALUES(:Station, :Station2, :Debut, :Fin, :Fichier) """, data)
        conn.commit()
        
        body = json.dumps({
                'title': '', \
                'img': '/'+fichier \
                 });
    
        # on envoie
        headers = [('Content-Type','application/json')];
        self.send(body,headers)
        
        
    else : 
        nom=str(fichier[0][0])
        body = json.dumps({
        'title': '', \
        'img': '/'+nom \
         });

        # on envoie
        headers = [('Content-Type','application/json')];
        self.send(body,headers)



  #
  # On envoie les entêtes et le corps fourni
  #
  def send(self,body,headers=[]):

    # on encode la chaine de caractères à envoyer
    encoded = bytes(body, 'UTF-8')

    # on envoie la ligne de statut
    self.send_response(200)

    # on envoie les lignes d'entête et la ligne vide
    [self.send_header(*t) for t in headers]
    self.send_header('Content-Length',int(len(encoded)))
    self.end_headers()

    # on envoie le corps de la réponse
    self.wfile.write(encoded)

 
#
# Instanciation et lancement du serveur
#
httpd = socketserver.TCPServer(("", 8081), RequestHandler)
httpd.serve_forever()


