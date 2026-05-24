# Nginx (Web site)

- Enable the site:
- - sudo ln -s /etc/nginx/sites-available/celestial-view /etc/nginx/sites-enabled/
- Test config:
- - sudo nginx -t
- Reload Nginx:
- - sudo systemctl reload nginx

## (Optional) HTTPS
- Use Certbot for free SSL:
- sudo apt install certbot python3-certbot-nginx
- sudo certbot --nginx -d example.com