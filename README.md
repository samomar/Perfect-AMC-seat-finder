# Perfect-AMC-seat-finder
Find the best AMC theaters seat for optimal movie viewing experience.

**Settings Explanation:**
**Trim:**
  If you choose 50 percent trim, it will trim 50 percent of the seats from the sides evenly,
      Because the goal is to find seats in the middle/center of the theatre.

**Seek days:** Amount of days into the future you want to crawl for show times.

**Print desired data:** for debugging reasons, if this is enabled, you'll see what columns and rows it tried to find.

**Movie name and theatre list:** You can obtain the accurate names from the URLs while you browse around AMC's website.

**theatre_types:** It will try to find shows and seats for only the theatre types you choose, types can be found in URLs.

**chair_type_filter:** If you or anyone you know is disabled, you may remove the 'Companion' and 'Wheelchair' filters.

# Requreiements:
beautifulsoup4==4.7.1
bs4==0.0.1
certifi==2019.3.9
chardet==3.0.4
html5lib==1.0.1
idna==2.8
requests==2.21.0
six==1.12.0
soupsieve==1.9.1
urllib3==1.24.2
webencodings==0.5.1
