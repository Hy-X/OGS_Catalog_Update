#!/usr/bin/env python
import urllib
import zipfile
import os
#testfile = urllib.URLopener()
#os.system("rm /home/analyst/www/staff/earthquake/earthquake.zip")
#testfile.retrieve("https://ogsweb.ou.edu/api/earthquake?mag=2&offset=48&format=shp", "/home/analyst/www/staff/earthquake/earthquake.zip")
#os.system("rm /home/analyst/www/staff/earthquake/earthquake.geojson")
#zip_ref = zipfile.ZipFile('/home/analyst/www/staff/earthquake/earthquake.zip', 'r')
#zip_ref.extractall('/home/analyst/www/staff/earthquake/')
#zip_ref.close()
#os.system("ogr2ogr -f GeoJSON -t_srs crs:84 /home/analyst/www/staff/earthquake/earthquake.geojson /home/analyst/www/staff/earthquake/earthquake.shp")
#os.system("echo 'eqfeed_callback(' > temp")
#os.system("echo ')' > temp2")
os.system("rm /home/analyst/www/staff/earthquake/past7days.jsonp")
os.system("cat /home/analyst/www/staff/earthquake/temp /home/analyst/www/eq/catalog/past7days/past7days.json /home/analyst/www/staff/earthquake/temp2 > /home/analyst/www/staff/earthquake/past7days.jsonp")

#filenames = [/home/analyst/www/staff/earthquake/temp /home/analyst/www/staff/earthquake/earthquake.geojson /home/analyst/www/staff/earthquake/temp2]
#with open('path/to/output/file', 'w') as outfile:
#    for fname in filenames:
#        with open(fname) as infile:
#            outfile.write(infile.read())


