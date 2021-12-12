#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Inderpreet Singh
"""

import os
from os.path import join, getsize
import sys
import subprocess
import pprint
from optparse import OptionParser
#import mutagen.id3 as id3
import stagger
from stagger.id3 import *
from stagger.tags import Tag23, Tag24
from clean_strings import prefix, patterns

import re, string

global_save_fields = ''
save_all = False

ss_genres = ['Dharmik', 'Shabad Kirtan', 'Dhadi Vaaran', 'Gurmat Veechar', 'Gurbani Uchaaran', 'Live Recorded']

def ss_genres_translate_numeric(s):
  genre = s
  if s != None:
    if s.isdigit():
      genre = ss_genres[int(s)-1]
    elif s.isalpha():
      if s not in ss_genres:
        print("Invalid genre: " + s)
        sys.exit(503)
      else:
        genre = s
  return genre
    

def removeNonAscii(s): return "".join(i for i in s if ord(i)<128)

def cyg2win(s):
  match = re.search('\/cygdrive\/([a-z])\/(.*)', s)
  s = "%s:/%s" % (match.group(1).upper(), match.group(2),)
  s = s.replace('/','\\')
  return s



def clean(s, times=1):
  for val in prefix:
    if val.endswith('='):
      s = s.replace(val.rstrip('='), '')
    else:
      fre = re.compile(re.escape(val), re.IGNORECASE)
      s = fre.sub('', s)
    s = s.strip()

  for vals in patterns:
    matchre = re.search(vals, s, re.IGNORECASE)
    if matchre:
      s = re.sub(r'(?i)' + vals, "", s)
      s = s.strip()
  
  s = s.strip()
  # s = removeNonAscii(s)
  s = s.strip('-').strip()
  
  if times == 1:
    times += 1
    return clean(s, times)
  
  return s

  
def ready(prompt):
  while True:
    s = input(prompt)
    if s == "Y" or s == "":
      return s

      
def save_changes(audio):
  audio.write()


def save_id3v1(filepath, v2):
  stagger.id3v1.Tag1.delete(filepath)


def tagFile(args):
  """
  Renames a file with the given options
  """
  sf = dict()
  sflist = dict()
  errors = []
  thedir = ''
  
  if os.path.isdir(args.files[0]):
    files = []
    thedir = os.path.abspath(args.files[0])
    for name in os.listdir(thedir):
      if os.path.isfile(os.path.join(thedir, name)) and os.path.splitext(name)[1].lower() == '.mp3':
        files.append(os.path.join(thedir, name))
  elif os.path.isfile(args.files[0]):
    files = args.files
  else:
    print("Weird arguments")
    sys.exit(1)
  
  
  if args.verbose:
    print(files)
  
  for filepath in files:
    sf[os.path.abspath(filepath)] = dict()
    sflist[os.path.abspath(filepath)] = dict()

  if not sf:
    print("Nothing to do")
    return False
  
  for filepath in sf.keys():
    print ("\n[+] ",)
    
    output = subprocess.check_output(["stagger", "-f", filepath], universal_newlines=True)
    print(output)
    
    try:
      audio = stagger.read_tag(filepath)
    except stagger.NoTagError:
      audio = stagger.default_tag()
    
    if audio.version == 4:
      output = subprocess.check_output(["eyeD3", "--to-v2.3", filepath], universal_newlines=True)
      print(output)
      audio = stagger.read_tag(filepath)


    global global_save_fields, save_all
    save_fields = []
    if not save_all:
      s = input("\nFields you want to save? [%s|%s] " % (('n' if global_save_fields else 'N'), global_save_fields,))
      if s != 'N' or s != 'n':
        if global_save_fields:
          if s == '':
            save_fields = global_save_fields
          else:
            save_fields = s.split(':')
            global_save_fields = save_fields
        else:
          if s != '':
            save_fields = s.split(':')
            global_save_fields = save_fields
          
    # process year
    match = re.search('([0-9]{4})', filepath)
    if match and match.group(1):
      year = match.group(1)
      if TYER in audio:
        year_tag = audio[TYER].text[0]
        if clean(year_tag) == '' or year_tag != year:
          audio[TYER] = year
      else:
        audio[TYER] = year
          
    # go through 'frame' args and save into sf
    if args.frame:
      for f in args.frame.split(':'):
        
        if args.setframe and f in args.setframe:
          print ("[-] %s: IGNORING setframe" % (f))
          continue
        
        if f in audio:
          # when list like USLT (lyricist)
          if isinstance(audio[f], list):
            # for key, val in enumerate(audio[f]):
              # if type(audio[f][key]).__name__ == 'USLT':
                # audio[f][key] = USLT(text=clean(str(audio[f][key].text)))
            print("[-] LIST %s" % (str(audio[f])))
          else:
            sf[filepath][f] = clean(str(audio[f].text[0]))
            print ("[-] %s: %s -> %s" % (f, str(audio[f].text[0]), sf[filepath][f]))
        else:
          print ("[-] %s: MISSING" % (f))

    if args.setframe:
      for setf in args.setframe.split(':'):
        (f, value) = setf.split('=')
        sf[filepath][f] = value
        print ("[-] %s: %s" % (f, value))

    # cleanup
    del_codes = [
      'TMOO', 'TPUB', 'TSRC', # blank
      #'TENC', # EAC
      'WPAY',
      # 'USLT',
      # 'TCOP',
      'WORS', 'WXXX', 'WOAF', 'WCOM', 'WOAR',
      'WOAS', 'TRSN',
      'TEXT', 'TOLY', 'TSSE', 'TKEY', 'TOAL', 'TIT3', 'TPE3', 'TIT1', # from VibeDesi
      'TPOS', 'TBPM',
      'TGID', 'TCAT', 'TDES', 'TDRL', 'TPE4', 'WFED', # RP
      'TCMP', # VipMunda
      'IPLS', # Mr-Khan.com
      # 'POPM', # WMP stores rating
      'PCST',
    ]
    

    print("Cleanup")
    retain = []
    delete = []
    for code in list(audio):
      if code in del_codes and code not in save_fields:
        delete.append(code)
      else:
        retain.append(code)

    print("\nDeleting: ")
    for code in delete:
      # print(code)
      try:
        print(str(audio[code]))
      except TypeError as ex:
        print("Something is wrong with audio[%s]." % (code,))
      del(audio[code])
    
    # delete useless comments
    if COMM in audio:
      for comment in audio[COMM][:]:
        if comment.desc == 'Catalog Number' or clean(comment.text).strip() == '':
          print("Removing comment: " + str(audio[COMM]))
          audio[COMM].remove(comment)
		  
    # delete useless APIC comments
    if APIC in audio:
      for apic in audio[APIC][:]:
        fix_desc = clean(apic.desc).strip()
        if fix_desc != apic.desc:
          print("Fixing picture desc: " + str(audio[APIC]))
          audio[APIC].desc = fix_desc
          print("Fixed picture desc: " + str(audio[APIC]))
		  
    # clean comments
    if USLT in audio:
      for uslt in audio[USLT][:]:
        fix_text = clean(uslt.text).strip()
        if fix_text == '':
          audio[USLT].remove(uslt)
          print ("Removed lyrics text: " + uslt.text)
        elif fix_text != uslt.text:
          print("Fixing lyrics  text: " + str(audio[USLT]))
          audio[USLT] = [fix_text]
          print("Fixed lyrics  text: " + str(audio[USLT]))
          sys.exit()
    
    if TXXX in audio:
      for txxx in audio[TXXX][:]:
        cleaned_txxx = clean(txxx.value)
        if txxx.description == 'EpisodeID' or cleaned_txxx == '' or txxx.description == '':
          print("Removed TXXX" + str(txxx))
          audio[TXXX].remove(txxx)
        elif cleaned_txxx != '' and cleaned_txxx != txxx.value:
          txxx.value = cleaned_txxx
          print ("Set TXXX" + str(txxx))

    # if args.verbose:
    print("\nRetaining: ")
    for code in retain:
      # print(code)
      if code in audio:
        print(str(audio[code]))


    artist_album_separator = '\/' if args.sikhsangeet else ' - '
    if args.verbose:
      print("Album Artist Separator: %s" % (artist_album_separator,))
    info_str = re.search('.*\/(.*)\.mp3', filepath)
    info_count = info_str.group(1).count(' - ')
    
    if info_count == 1:
      regex = '.*\/(?P<artist>.*?) - (?P<title>.*?).mp3'
      match = re.search(regex, filepath)
      if match == None:
        print ("Filename does not fit pattern: %s" % (regex,))
      # print(match.groups())
      artist = match.group('artist')
      audio[TOPE] = [ artist ]
      audio[TPE2] = [ artist ] # album artist
      if 'TCOM' in audio and audio['TCOM'].text[0] == '':
        del(audio['TCOM'])
        
      tracknr = "01"
      title = match.group('title')
      
      print("album %s", (audio.album,))
      album = clean(audio.album) # album is usually not in filename for singles, alternatively we can use filename's title
      
      print("album after %s", (album,))
      
    elif info_count == 2:
      regex = '.*\/(?P<album_artist>.*?)%s(?P<album>[^\/]+)\/(?P<nr>.*?) - (?P<artist>.*?) - (?P<title>.*?).mp3' % (artist_album_separator,)
      match = re.search(regex, filepath)
      if match == None:
        print ("Filename does not fit pattern: %s" % (regex,))
      # print(match.groups())

      album_artist = match.group('album_artist')
      artist = match.group('artist')
      audio[TOPE] = [ album_artist ]
      audio[TPE2] = [ album_artist ] # album artist
      if 'TCOM' in audio and audio['TCOM'].text[0] == '':
        del(audio['TCOM'])

      album = match.group('album')
      tracknr = match.group('nr')
      title = match.group('title')
    else:
      match = re.search('.*\/(?P<tpe>.*?)%s(?P<album>[^\/]+)\/(?P<nr>.*?) - (?P<tcom>.*?) - (?P<title>.*?) - (?P<tope>.*?).mp3' % (artist_album_separator,), filepath)
      # print(match.groups())

      album_artist = match.group('tpe')
      audio[TPE2] = [ album_artist ] # album artist

      artist = '%s - %s' % (match.group('tcom'), match.group('tope'),)
      audio[TCOM] = [ match.group('tcom') ]
      audio[TOPE] = [ match.group('tope') ]

      album = match.group('album')
      tracknr = match.group('nr')
      title = match.group('title')

    audio[TPE1] = [ artist ]
    audio.artist = artist
    audio[TALB] = [ album ]
    audio.album = album
    audio[TRCK] = [ tracknr ]
    audio.track = tracknr
    audio[TIT2] = [ title ]
    audio.title = title
    
    default_genre = 'Bhangra'
    audio[TCON] = args.sikhsangeet if args.sikhsangeet else default_genre
    audio.genre = args.sikhsangeet if args.sikhsangeet else default_genre
    
    audio.comment = 'SikhSangeet.com' if args.sikhsangeet else 'DholCutzRadio.com'


    for f in sf[filepath].keys():
      val = sf[filepath][f]
      print ("[-] %s: %s" % (f, val))
      if f == "COMM":
        audio.comment = val
      else:
        audio[eval(f)] = [ val ]
    
    artist = str(audio['TPE1'].text[0])
    artist_clean = artist.strip().strip('-').strip()
    if artist != artist_clean:
      print ("[-] TPE1 Clean: %s" %(artist_clean))
      audio[TPE1] = [ artist_clean ]

    print ("\nSaving: ")
    ignore_codes = [
      'RGAD', # replaygain, no text
      'MCDI', # CD header info for CDDB matching
    ]
    for code in audio:
      print (code)
      if code in audio:
      
        if not isinstance(audio[code], list) and code not in ignore_codes:
          cleaned_text = clean(audio[code].text[0])
          if cleaned_text != audio[code].text[0]:
            audio[code] = [ cleaned_text ]
        print (str(audio[code]))

    save_id3v1(filepath, audio)
    
    if save_all:
      save_changes(audio)
    else:
      s = input("\nSave? [Yna] ")
      if s == 'Y' or s == '' or s == 'a':
        if s == 'a':
          save_all = True
        save_changes(audio)
  
  return True

  
  
if __name__ == "__main__":
  """
  Parses command line and renames the files passed in
  """
  # create the options we want to parse
  import argparse
  parser = argparse.ArgumentParser()
  parser.add_argument("files", nargs='+',
                      help="list of files to be tagged")
  parser.add_argument("-f", "--frame", type=str, default="",
                      help="Frames separated by comma: TCOP:TCOM")
  parser.add_argument("-ss", "--sikhsangeet", type=str,
                      help="Adds the Sikh Sangeet comment with the parameter as Genre [%s]" % (', '.join(ss_genres)))
  parser.add_argument("-s", "--setframe", type=str,
                      help="TOPE=Juice Wala:TCOM=Pani Wala")
  parser.add_argument("-v", "--verbose", action="store_true",
                      help="increase output verbosity")
  args = parser.parse_args()
  
  args.sikhsangeet = ss_genres_translate_numeric(args.sikhsangeet)
  
  print ("\nFixing tags: %s\n" % (args.frame if args.frame else "None"))
  print ("Setting tags: %s\n" % (args.setframe if args.setframe else "None"))
 
  # check that they passed in atleast one file to rename
  if len(args.files) < 1:
    print ("Files to tag not specified")
    sys.exit(0)
  print("\nWorking with: %s\n" % (args.files,))

  # loop though the files and rename them
  tagFile(args)
  
  # exit successful
  sys.exit(0)
