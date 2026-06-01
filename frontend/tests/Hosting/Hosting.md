# Manual upgrade

## Download
```
wget https://github.com/JECastle4/Castle-Celestial-View/releases/download/v1.0.2/astronomy_tools-1.0.2-py3-none-any.whl
wget https://github.com/JECastle4/Castle-Celestial-View/releases/download/v1.0.2/castle-celestial-view-frontend-v1.0.2.zip
```

## Stop services
```
sudo systemctl stop nginx
sudo systemctl stop celestial-api
```

## Deploy
### remove dist
```
rm -rf dist
```

### unzips to dist
```
unzip castle-celestial-view-frontend-v1.0.2.zip
```
### upgrade whl
```
pip install astronomy_tools-1.0.2-py3-none-any.whl
```

## Restart
```
sudo systemctl start celestial-api
sudo systemctl start nginx
```

# Configure
## Nginx (Web site)
- Enable the site:
- - sudo ln -s /etc/nginx/sites-available/celestial-view /etc/nginx/sites-enabled/
- Test config:
- - sudo nginx -t
- Reload Nginx:
- - sudo systemctl reload nginx

### (Optional) HTTPS
- Use Certbot for free SSL:
- sudo apt install certbot python3-certbot-nginx
- sudo certbot --nginx -d example.com

## Enable port 80:
sudo ufw allow 80/tcp
sudo ufw reload

## Disable port 80
sudo ufw deny 80/tcp
sudo ufw reload