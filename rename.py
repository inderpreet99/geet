#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Inderpreet Singh
Date:   2011
Renames files based on the input options.
"""

import os
import sys
import subprocess
import pprint
import calendar
from optparse import OptionParser
from clean_strings import prefix, patterns

import re, string

import stagger
from stagger.id3 import *


class IPSRename:
  seq: int = 1

  def pad_tens(self, n) -> str:
    return str(n) if n >= 10 else "0"+str(n)

  def month_name_to_num(self, filename):
    for k, month_name in enumerate(calendar.month_name):
      if not month_name:
        continue
      if month_name in filename:
        filename = filename.replace(month_name, self.pad_tens(k))

    for k, month_name in enumerate(calendar.month_abbr):
      if not month_name:
        continue
      if month_name in filename:
        filename = filename.replace(month_name, self.pad_tens(k))
   
    return filename
      
    
  def ireplace(self, str, sub, rep):
    subcomp = re.compile(re.escape(sub), re.IGNORECASE)
    str = subcomp.sub(rep, str)
    return str

  def RenameFile(self, options, filepath):
    """
    Renames a file with the given options
    """
    # split the pathname and filename
    if os.path.isfile(filepath):
      name_filepath, ext_filepath = os.path.splitext(filepath)
    else:
      name_filepath = filepath
      ext_filepath = ''
  
    pathname = os.path.dirname(filepath)
    replaced = []
    filename = os.path.basename(filepath).replace(ext_filepath, '')
    errors = []
    
    if options.tag:
      try:
        audio = stagger.read_tag(filepath)
      except stagger.NoTagError:
        audio = stagger.default_tag()
    
      output = subprocess.check_output(["stagger", "-f", filepath], universal_newlines=True)
      print(output)
      
      try:
        track_no = audio[TRCK] + " - "
      except Exception as ex:
        track_no = ""
      filename = "%s%s - %s" % (track_no, audio.artist, audio.title,)
    
    if options.zero:
      numre = re.search("^[0-9]+", filename)  #get the starting number
      if numre:
        num = numre.group(0)
        if num.isdigit():  # if its a number 
        
          if len(num) == 1: # if only 1 digit
            filename = '0' + filename      # prepend 0
            num = "0"+num
            replaced.append("prepend 0")
      else:
        filename = '00 - ' + filename
        replaced.append("prepend 00")

    if options.artist:
      numpart_regex = "^[^a-z]*"
      numpartre = re.search(numpart_regex, filename, re.IGNORECASE)  #get the starting number
      if numpartre:
        numpart = numpartre.group(0)
        if not numpart[0:2].isdigit():
          filename = options.artist[0] + " - " + filename
          replaced.append("added artist to the start")
        if numpart.find(' - ') != -1 and numpart[0:2].isdigit():
          filename = re.sub(numpart, numpart + options.artist[0] + " - ", filename)
          replaced.append("added artist in the middle")
        else:
          errors.append("can't add artist")
          
    
    # trim characters from the front
    if options.trimfront:
      filename = filename[options.trimfront:]

    # trim characters from the back
    if options.trimback:
      filename = filename[:len(filename)-options.trimback]

    # replace values if any
    if options.replace:
      for val in options.replace:
        filename = filename.replace(val[0], val[1])

    # convert to lowercase if flag set
    if options.lowercase:
      filename = filename.lower()

    # cleanup
    if options.clean:
      #for char in prefix:
        #print str(ord(char)) +  "--------------------" + char
      #  print char
      #for char in filename[1]:
      #  print str(ord(char)) + "--------------------" + char
      
      for val in prefix:
        last_filename = filename
        if val.endswith('='):
          filename = filename.replace(val.rstrip('='), '')
        else:
          fre = re.compile(re.escape(val), re.IGNORECASE)
          filename = fre.sub('', filename)
        filename = filename.strip()
        
        if "useless str" not in replaced and last_filename != filename:
          replaced.append("useless str")
        
      for val in patterns:
        matchre = re.search(val, filename)
        # match_covers = os.path.splitext(filepath)[1].lower() == '.jpg'
      
        if matchre and (os.path.splitext(filepath)[1].lower() != '.jpg'):
          if options.verbose:
            print(val + ' before: ' + filename)
          filename = re.sub (val, "", filename)
          if options.verbose:
            print(val + ' after: ' + filename)
          replaced.append(val + "")
          #print("\nfilename regex replaced " + val + ": " + filename)
          filename = filename.strip()
      
      if not options.skip_drdj and (' Dr.' in filename or ' DJ ' in filename):
        last_filename = filename
        filename = filename.replace(' Dr.', ' Dr').replace(' DJ ', ' Dj ')
        if "drdj" not in replaced and last_filename != filename:
          replaced.append("drdj")
      
      if ', ' in filename:
        last_filename = filename
        filename = filename.replace(', ', ' & ')
        if "comma" not in replaced and last_filename != filename:
          replaced.append("comma")
      
      # Capitalize words
      if options.cap:
        last_filename = filename
        words = filename.split()
        for idx, w in enumerate(words):
          if w.lower() == w:
            words[idx] = w.capitalize()
        filename = ' '.join(words)
        if last_filename != filename:
          replaced.append('Cap')
      
      last_filename = filename
      filename = filename.replace('Late ', '')
      if last_filename != filename:
        replaced.append('Late Singer')
      
      
      filename = filename.strip()
      filename = filename.replace('--', '-')
      filename = filename.replace('- -', '-')
      filename = filename.replace('  ', ' ')
      #filename = filename.replace('-.mp3', '.mp3')
      #filename = filename.replace('- .mp3', '.mp3')
      filename = filename.strip('-').strip()
      
    if options.date:
      filename_fixed = self.month_name_to_num(filename)
      if filename != filename_fixed:
        filename = filename_fixed
        replaced.append("Month name to num")
    
    if options.seq:
      counts = re.search("([0]+)#", options.seq_format)
      filler = counts.group(1) + "#"
      pad = len(filler)
      filename_fixed = re.sub(options.seq_regex, options.seq_format.replace(filler, str(self.seq).zfill(pad)), filename)
      
      if filename != filename_fixed:
        filename = filename_fixed
        replaced.append("Added sequence")
        self.seq += 1
      
    if options.dash:
      if '_' in filename:
        filename = filename.replace('_', ' ')
        replaced.append('removed underscores')
      
      numre = re.search("^[0-9]+", filename)  #get the starting number
      if numre:
        num = numre.group(0)
        # print num
        if num.isdigit():  # if its a number
          # add dash after the track number if missing
          numpart_regex = "^[^a-z]*"
          numpartre = re.search(numpart_regex, filename, re.IGNORECASE)  #get the starting number
          if numpartre:
            numpart = numpartre.group(0)
            if numpart.find(' - ') == -1:
              filename = re.sub(re.compile(numpart_regex, re.IGNORECASE), num + " - ", filename)
              replaced.append("add dashes")
      
      
      # TODO: Error "TypeError: 'dict_keys' object does not support indexing" happens when doing hello-sign type of replacements
      dash_regexs = {
        "[^\s]\-[^\s]": {
          "-": " - ",
        },
        "\s\-[^\s]": {
          " -": " - ",
        },
        "[^\s]\-\s": {
          "- ": " - ",
        },
      }
      dash_exceptions = [
        "Tru-Skool",
        "Manak-E",
        "Hi-Fi",
      ]
      for dash_regex in dash_regexs:
        no_space_dash = re.search(dash_regex, filename)
        if no_space_dash:
          exc_match = False
          for dash_exc in dash_exceptions:
            (before, partition, after,) = dash_exc.partition('-')
            dash_pos = filename.find(no_space_dash.group(0))
            exc_parsed = filename[dash_pos-len(before)+1:dash_pos+len(after)+2]
            if exc_parsed == dash_exc:
              exc_match = True
              replaced.append("dash skip: " + dash_exc)
          
          if exc_match:
            continue
            
          # list(b) is the same as dict[key].keys()[0], but works in py3
          filename = filename.replace(no_space_dash.group(0), no_space_dash.group(0).replace(list(dash_regexs[dash_regex])[0], ' - '))
          replaced.append("add dashspace")
    
    
    if options.feat:
      featstrs = [ ' featuring', ' feat.', ' (feat.', ' feat', ' (feat', ' ft.', ' ft', ]
        # ' (featuring', ' (feat.', ' (feat', ' (ft.', ' (ft', ]
      first_feat_pos = -1
      rep_char = '-' if options.feat == 2 else '&'
      
      for featstr in featstrs:
        if featstr in filename.lower():
          last_filename = filename
          pos = filename.find(featstr.lower())
          if pos > first_feat_pos:
            first_feat_pos = pos
          filename = self.ireplace(filename, featstr, rep_char)
          
          # replace the parenthesis
          if filename != last_filename:
            new_filename = filename[first_feat_pos:].replace(')', '')
            filename = filename[:first_feat_pos] + new_filename
          
          if rep_char in filename:
            filename = filename.replace(rep_char, ' ' + rep_char + ' ').replace('  ', ' ')
        
          if "featuring" not in replaced and last_filename != filename:
            replaced.append("featuring")
          
          if options.feat == 1:
            filename = re.sub("([0-9]*) \- (.*?) \- (.*?) \\" + rep_char + "(.*?)\)?$", r"\1 - \2 & \4 - \3", filename)
            replaced.append("featuring shuffle")

    if options.acronym:
      last_filename = filename
      #filename = re.sub('\.(?!(\S[^. ])|\d)', '', filename)
      m=re.search('(.*?)(([a-zA-Z]\.){2,})(.*)', filename)
      if m:
          replacement=''.join(m.group(2).split('.'))
          filename=m.group(1)+replacement+m.group(4)
      if last_filename != filename:
        replaced.append('Acronym Dots')

    # weird replacements
    if 'A S Kang' in filename:
      filename = filename.replace('A S Kang' , 'AS Kang')
      replaced.append('ASKang')
      
    if options.regex:
      last_filename = re.sub(options.regex[0][0], options.regex[0][1], filename)
      if last_filename != filename:
        replaced.append('Regex replace')
        filename = last_filename
            
    if options.bracket:
      brackets_regex = re.search("\[(.*)\]", filename)
      if brackets_regex:
        filename = filename.replace(brackets_regex.group(0), "- " + brackets_regex.group(1))
    
    if options.shuffle:
      shuffle = options.shuffle[0]
      fn_split = filename.split(options.shuffle_delimiter)
      hy_nums = list(shuffle)
      while len(fn_split) < len(hy_nums):
        shuffle = shuffle.replace(str(len(hy_nums)-1), '')
        hy_nums = list(shuffle)
        
      hy_fmt = "{" + ("}" + options.shuffle_delimiter + "{").join(hy_nums) + "}"
      
      filename = hy_fmt.format(*fn_split)
      replaced.append('Shuffle')
      
    if options.suffix:
      filename += options.suffix
      
    if options.prefix:
      filename = options.prefix + filename
      
    while '  ' in filename:
      filename = filename.replace('  ', ' ')

    # add extension back
    filename += ext_filepath.lower()
    
    # create the new pathname and rename the file
    new_filepath = os.path.join(pathname, filename)
    try:
      # check for verbose output
      
      if os.path.isfile(filepath):
        
        # print("'%s'" % filename)
        # print("ext filepath: %s" % ext_filepath)
          
        new_filepath = new_filepath.replace(' ' + ext_filepath, ext_filepath)
        new_filepath = new_filepath.replace(ext_filepath + ' ', ext_filepath)
        
      if options.verbose:
        print("[-] Old: %s" %(filepath))
        if filepath != new_filepath:
          print("[+] New: %s" %(new_filepath))
        if replaced:
          print("Cleaned: %s" % (", ".join(replaced)))
        if errors:
          print("Errors: %s" % (", ".join(errors)))
      
      if options.go:

        if filepath != new_filepath and os.path.exists(new_filepath):
          fileName, fileExtension = os.path.splitext(new_filepath)
          new_filepath = fileName + "-2" + fileExtension
          print("Filepath collision: " + new_filepath)

        os.rename(filepath, new_filepath)
	  
      print("")
    except OSError as ex:
      print >>sys.stderr, "Error renaming '%s': %s"  % (filepath, ex.strerror)

  def __init__(self):
    """
    Parses command line and renames the files passed in
    """
    # create the options we want to parse
    usage = "usage: %prog [options] file1 ... fileN"
    optParser = OptionParser(usage=usage)
    optParser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=True,
                          help="Use verbose output")
    optParser.add_option("-l", "--lowercase", action="store_true", dest="lowercase", default=False,
                          help="Convert the filename to lowercase")
    optParser.add_option("-f", "--trim-front", type="int", dest="trimfront", metavar="NUM",
                          help="Trims NUM of characters from the front of the filename")
    optParser.add_option("-b", "--trim-back", type="int", dest="trimback", metavar="NUM",
                          help="Trims NUM of characters from the back of the filename")
    optParser.add_option("-k", "--bracket", action="store_true", dest="bracket", default=False,
                          help="Turns brackets into dashes")
    optParser.add_option("-r", "--replace", action="append", type="string", nargs=2, dest="replace",
                          help="Replaces OLDVAL with NEWVAL in the filename", metavar="OLDVAL NEWVAL")
    optParser.add_option("-a", "--artist", action="append", type="string", nargs=1, dest="artist",
                          help="Adds artist after the track number in the filename", metavar="Artist")
    optParser.add_option("--cap", action="store_true", dest="cap", default=False,
                          help="Capitalize Title case")
    optParser.add_option("-c", "--clean", action="store_true", dest="clean", default=True,
                          help="Clean the file names")
    optParser.add_option("-t", "--tag", action="store_true", dest="tag", default=False,
                          help="Rename files from tag")
    optParser.add_option("--feat", type="int", dest="feat", metavar="NUM",
                          help="Handles featuring artists (1 or 2 artist)")
    optParser.add_option("--acronym", action="store_true", dest="acronym", default=True,
                          help="Change A.S. To AS")
    optParser.add_option("-s", "--shuffle", action="append", type="string", nargs=1, dest="shuffle",
                          help="Shuffle the filename. For, example 210 would reorder backwards.")
    optParser.add_option("--shuffle-delimiter", action="store", type="string", dest="shuffle_delimiter", default=" - ",
                          help="Shuffle delimiter. Default: ' - '")
    optParser.add_option("--regex", action="append", type="string", nargs=2, dest="regex",
                          help="Regex replace strings")
    optParser.add_option("-z", "--zero", action="store_true", dest="zero", default=False,
                          help="Add zeros to the track number (if needed)")
    optParser.add_option("-d", "--dash", action="store_true", dest="dash", default=False,
                          help="Adds dash after the track number (if needed)")
    optParser.add_option("--skip-drdj", action="store_true", dest="skip_drdj", default=False,
                          help="Skip the drdj filter")
    optParser.add_option("--seq", action="store_true", dest="seq", default=False,
                          help="Sequence the files")
    optParser.add_option("--seq-regex", action="store", type="string", dest="seq_regex", default="$",
                          help="Sequence the files with the provided regex for positioning. ^ for prefix, $ for suffix (default) or provide full regex like .+")
    optParser.add_option("--seq-format", action="store", type="string", dest="seq_format", default=" - 0#",
                          help="Format the sequence with padded 0s. Add delimiters as you like.")
    optParser.add_option("--seq-start", type="int", dest="seq_start", metavar="NUM",
                          help="The starting number of the sequence")

    optParser.add_option("--suffix", action="store", type="string", dest="suffix", default="",
                          help="Add suffix")
    optParser.add_option("--prefix", action="store", type="string", dest="prefix", default="",
                          help="Add prefix")
    optParser.add_option("-g", "--go", action="store_true", dest="go", default=False,
                          help="Just go do it!")
    optParser.add_option("--date", action="store_true", dest="date", default=False,
                          help="Change month names to month numbers")
    optParser.add_option("--mp3", action="store_true", dest="mp3", default=False,
                          help="Add default flags for mp3")
    (options, args) = optParser.parse_args()
   
    # check that they passed in atleast one file to rename
    if len(args) < 1:
      optParser.error("Files to rename not specified")
      
    if options.mp3:
      options.dash = True
      options.comma = True
      options.cap = True
     
    if options.seq_start:
      self.seq = options.seq_start

    # loop though the files and rename them
    for filename in args:
      if os.path.exists(filename):
        self.RenameFile(options, filename)
      else:
        print("Invalid path: %s" %(filename,))
  
if __name__ == "__main__":
  r = IPSRename()
  sys.exit(0)
