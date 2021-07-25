from glob import glob
from os import path
from PIL import Image
from os import listdir
from os.path import isfile, join

###
### Compile BDF fonts to c header files
###

# This code is available under the MIT license
# Copyright (c) 2019 Peter Vullings (Projectitis)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Will create a header file for each bdf font file, either
# as a bdffont_t.

# Many thanks to original c code from Paul Stoffregen used as reference
# https://github.com/PaulStoffregen/ILI9341_t3/blob/master/extras/bdf_to_ili9341.c


#####################################################################################
# Ugly hack from https://github.com/projectitis/packedbdf
#
# Vindar, 2021
#
# Procedure to generate the font file. 
#
# 1 - Obtain the font in .ttf format (from google font for instance).  
#
# 2 - Convert the font to bdf (possibly with anti-aliasing).
#     The font must be regular (not variable type). 
#
#   (a) Open fontforge and load the font.  
#   (b) [Encoding] -> [compact] (to remove undefined glyphs)
#   (c) [Elements] -> [Bitmaps stikes available]
#        in "Point size 72 dpi", put the required size to generate separated by commas, 
#        add @2 for 2bit antialiased font and @4 for 4 bit antialiased font.
#        For this library, we use:
#        8,9,10,11,12,14,16,18,20,24,28,32,36,8@2,9@2,10@2,11@2,12@2,14@2,16@2,18@2,20@2,24@2,28@2,32@2,36@2,8@4,9@4,10@4,11@4,12@4,14@4,16@4,18@4,20@4,24@4,28@4,32@4,36@4 
#        Leave other fields as default. 
#   (d)  [File] -> [Generate Font]
#         keep proposed name / no outline font / BDF
#         and after hitting "generate",set 72 for BDF resolution 
#
# 3 - copy all the .bdf files to use in the "bdf/" sub-directory and run the script from "/tools".  
#     The .h and .cpp file are created inside "/src"
#     The file "font-list.html" is created in the root dir "..". 
#####################################################################################

extern = not (__name__ == '__main__')


# debug
debug = False
def log(*args):
    global debug
    if debug:
        print(*args)


# function defs
def bits_required_unsigned( max ):   
    n = 1;
    if (max < 0): max = 0
    while max >= (1 << n): n+=1
    return n


def bits_required_signed(min, max):
    n = 2;
    if (min > 0): min = 0;
    if (max < 0): max = 0;
    while min < -(1 << (n-1)): n+=1
    while max >= (1 << (n-1)): n+=1
    return n


def pixel(glyph, x, y):
    if x >= glyph['width']: return 0;
    if y >= glyph['height']: return 0;
    # grab the correct byte
    #b = glyph['data'][(((glyph['width'] + 7) >> 3) * y) + (x >> 3)];
    b = glyph['data'][(((glyph['width']*bits_per_pixel + 7) >> 3) * y) + (x >> (3-bpp_index))];
    # firstly, adjust x to current byte
    x = x % pix_per_byte
    # now move pixel to least significant spot
    b = b >> int((pix_per_byte-x-1)*bits_per_pixel)
    # finally return pixel value using mask
    b = b & bpp_mask
    return b


def output_newline():
    global output_state_linelen, outstr
    if output_state_linelen > 0:
        outstr += '\n'
        output_state_linelen = 0


def output_bit(bit):
    global output_state_byte, output_state_bytecount, output_state_bitcount, output_state_linelen, outstr

    bitmask = 1 << (7 - output_state_bitcount)
    if bit: output_state_byte |= bitmask;
    else: output_state_byte &= ~bitmask;
    
    output_state_bitcount += 1
    if output_state_bitcount >= 8:
        output_state_bitcount = 0
        outstr += '0x'+format(output_state_byte, '02x')+','
        output_state_bytecount+=1
        output_state_linelen+=1
        if output_state_linelen >= 10: output_newline()
        output_state_byte = 0



def output_number(num,bits):
    while bits > 0:
        output_bit(num & (1 << (bits-1)))
        bits -= 1


def output_line(glyph,y):
    for x in range(0, glyph['width']):
        output_number(pixel(glyph, x, y),bits_per_pixel)


def output_pad_to_byte():
    global output_state_bitcount
    while (output_state_bitcount > 0): output_bit(0)


def lines_identical(glyph,y1,y2):
    for x in range(0, glyph['width']):
        if (pixel(glyph, x, y1) != pixel(glyph, x, y2)): return 0
    return 1


def num_lines_identical(glyph,y):
    y2 = y+1
    for y2 in range(y+1, glyph['height']):
        if not lines_identical(glyph, y, y2): break
    return y2 - y - 1


def output_glyph(glyph):
    output_number(0, 3) # reserved bits, intended to identify future formats
    output_number(glyph['width'], bits_width)
    output_number(glyph['height'], bits_height)
    output_number(glyph['xoffset'], bits_xoffset)
    output_number(glyph['yoffset'], bits_yoffset)
    output_number(glyph['delta'], bits_delta)

    # Change for v2.3
    # AA fonts have pixel data aligned to byte boundary, and don't have leading
    # bit to indicate duplicate lines (i.e. duplicate lines are not supported).
    y = 0
    if bits_per_pixel==1:
        while y < glyph['height']:
            identical_count = num_lines_identical(glyph, y);
            if (identical_count == 0):
                output_bit(0)
                output_line(glyph, y)
            else:
                output_bit(1)
                if identical_count > 6: identical_count = 6;
                output_number(identical_count - 1, 3)
                output_line(glyph, y)
                y += identical_count
            y+=1
    else:
        output_pad_to_byte()
        while y < glyph['height']:
            output_line(glyph, y)
            y+=1

    output_pad_to_byte()




outstr = ''
output_state_byte = 0
output_state_bitcount = 0
output_state_linelen = 0
output_state_bytecount = 0

bits_width = 0
bits_height = 0
bits_xoffset = 0
bits_yoffset = 0
bits_delta =  0

bits_per_pixel = 1 
bpp_index = 0    
bpp_mask = 0b00000001
pix_per_byte = 8
    
# Process file `file` and name the font `font_name`
#
# Return a string with the .c file content
#
def dofile(file, fontname, ch_index_min, ch_index_max):
 
    global outstr
    global output_state_byte
    global output_state_bitcount
    global output_state_linelen
    global output_state_bytecount

    global bits_width
    global bits_height
    global bits_xoffset
    global bits_yoffset
    global bits_delta

    global bits_per_pixel 
    global bpp_index
    global bpp_mask
    global pix_per_byte
    
    
    # Some useful messages to console
    print()
    print('Processing font: ',file)
    
    # Open raw file and grab properties
    outstr = ''
    output_state_byte = 0
    output_state_bitcount = 0
    output_state_linelen = 0
    output_state_bytecount = 0

    glyphs = {}
    glyph_data = []
    process_glyph = False
    process_data = False

    line_space = 0
    cap_height = 0
    is_bold = False
    is_italic = False
    font_size = 0
    font_name = ''
    
    version = 1
    bits_per_pixel = 1 
    bpp_index = 0    
    bpp_mask = 0b00000001
    pix_per_byte = 8
      
    found_ascent = False
    font_ascent = 0
    found_descent = False
    font_descent = 0
    found_encoding = False
    encoding = 0
    found_dwidth = False
    dwidth_x = 0
    dwidth_y = 0
    found_bbx = False
    bbx_width = 0
    bbx_height = 0
    bbx_xoffset = 0
    bbx_yoffset = 0
    linenum = 0
    expect_line = 0
    expect_bytes = 0
    encoding_start1 = 0
    encoding_end1 = 0
    encoding_start2 = 0
    encoding_end2 = 0
    font_name = ""
    first_time = True
    
    with open(file, "rt") as f:
        for line in f:
            linenum += 1
            prop = line.split(" ", 1)
            if len(prop)>0:
                prop[0] = prop[0].strip()
            if len(prop)>1:
                prop[1] = prop[1].strip()
                props = prop[1].split(" ")
            else: props = []

            # process font header
            if not process_glyph:
                # Exit header mode (enter glyph mode)
                if prop[0] == 'STARTCHAR':
                    found_encoding = False
                    found_dwidth = False
                    found_bbx = False
                    process_data = False
                    process_glyph = True
                    if first_time: 
                        print('  FONT_NAME:'+font_name+', SIZE:'+str(font_size)+', '+str(bits_per_pixel)+'bpp')
                        first_time=False                        
                    log('  FOUND',prop[1])
                # Collect header properties
                elif prop[0] == 'SIZE':
                    font_size = int(props[0])
                elif prop[0] == 'FAMILY_NAME':
                    font_name = prop[1].strip().strip('\"').replace(' ','')
                elif prop[0] == 'WEIGHT_NAME':
                    if 'Bold' in prop[1]:
                        is_bold = True
                elif prop[0] == 'SLANT':
                    if '\"I\"' in prop[1]:
                        is_italic = True
                elif prop[0] == 'BITS_PER_PIXEL':
                    bits_per_pixel = int(prop[1])
                    if (bits_per_pixel>1):
                        version = 23
                        if (bits_per_pixel==2): bpp_index = 1
                        elif (bits_per_pixel==4): bpp_index = 2
                        elif (bits_per_pixel==8): bpp_index = 3
                        else: raise Exception('BITS_PER_PIXEL not supported, at line '+str(linenum))
                        bpp_mask = (1 << bits_per_pixel)-1
                        pix_per_byte = 8/bits_per_pixel
                elif prop[0] == 'FONT_ASCENT':
                    found_ascent = True
                    font_ascent = int(prop[1])
                elif prop[0] == 'FONT_DESCENT':
                    found_descent = True
                    font_descent = int(prop[1])

            # process glyphs 
            elif not process_data:
                # Encoding is the ascii number
                if prop[0] == 'ENCODING':
                    found_encoding = True
                    encoding = int(prop[1])
                    log('    Encoding',encoding) 
                    
#                    if (encoding >= ch_index_min) and (encoding <= ch_index_max): 
#                        if encoding_start2>0:
#                            if encoding != (encoding_end2+1): raise Exception('ENCODING more than 2 encoding ranges ('+str(encoding_start1)+'-'+str(encoding_end1)+', '+str(encoding_start2)+','+str(encoding_end2)+'), at line '+str(linenum))
#                            encoding_end2 = encoding
#                        elif encoding_start1>0:
#                            if encoding != (encoding_end1+1):
#                                encoding_start2 = encoding
#                                encoding_end2 = encoding
#                            else:
#                                encoding_end1 = encoding
#                        else:
#                            encoding_start1 = encoding
#                            encoding_end1 = encoding                
                 
                elif prop[0] == 'DWIDTH':
                    found_dwidth = True
                    dwidth_x = int(props[0])
                    dwidth_y = int(props[1])
                    log('    DWIDTH',dwidth_x,dwidth_y)
                    if (dwidth_x < 0): raise Exception('DWIDTH x negative, at line '+str(linenum))
                    if (dwidth_y != 0): raise Exception('DWIDTH y not zero, at line '+str(linenum))
                elif prop[0] == 'BBX':
                    found_bbx = True
                    bbx_width = int(props[0])
                    bbx_height = int(props[1])
                    bbx_xoffset = int(props[2])
                    bbx_yoffset = int(props[3])
                    log('    BBX',bbx_width,bbx_height,bbx_xoffset,bbx_yoffset)
                    if (bbx_width < 0): raise Exception('BBX width negative, line '+str(linenum))
                    if (bbx_height < 0): raise Exception('BBX height negative, line '+str(linenum))
                elif prop[0] == 'BITMAP':
                    log('    BITMAP')
                    if not found_encoding: raise Exception('missing ENCODING, line '+str(linenum))
                    if not found_dwidth: raise Exception('missing DWIDTH, line '+str(linenum))
                    if not found_bbx: raise Exception('missing BBX, line '+str(linenum))
                    expect_lines = bbx_height
                    expect_bytes = ((bbx_width * bits_per_pixel) + 7) >> 3
                    glyph_data = []
                    process_data = True

            # process glyph data
            else:
                if expect_lines > 0 and expect_bytes > 0:
                    data = prop[0]
                    for i in range(expect_bytes):
                        try:
                            glyph_data.append( int(data[0:2],16) )
                        except:
                            raise Exception('Non-hex char on line, line '+str(linenum))
                        data = data[2:]
                    expect_lines -= 1
                else:
                    if prop[0] == 'ENDCHAR':
                        process_glyph = False
                        if (encoding >= ch_index_min) and (encoding <= ch_index_max):
                        #keep this glyph
                            glyphs[str(encoding)] = { 'width': bbx_width, 'height': bbx_height, 'xoffset': bbx_xoffset, 'yoffset': bbx_yoffset, 'delta': dwidth_x, 'encoding': encoding, 'data': glyph_data }
                    else:
                        raise Exception('ENDCHAR expected, line '+str(linenum))

        if found_ascent and found_descent:
            line_space = font_ascent + font_descent
        # Capital E is char 69. This is used for general 'cap height'
        if '69' in glyphs and 'data' in glyphs['69']:
            cap_height = glyphs['69']['height'] + glyphs['69']['yoffset']

    # File finished processing
    log('  Line space:',line_space)
    log('  Cap height:',cap_height)
    
    if '32' not in glyphs.keys():
        raise Exception('missing [SPACE] glyph')

    abs_min_ch = 0
    abs_max_ch = 0    
    bestgap_start = -1
    bestgap_end = -1
    bestgap_l = -1
    gap_start = -1
        
    oldglyphs = glyphs    
    glyphs = {}
        
    for i in range(ch_index_min,ch_index_max+1): 
        si = str(i)
        
        if si in oldglyphs.keys():
            # glyph si found
            glyphs[si] = oldglyphs[si]
            if abs_min_ch==0: abs_min_ch = i
            abs_max_ch = i

            if gap_start != -1:
                # end of gap
                #print("gap found : [" , gap_start, ' , ', i - 1 , ']')
                if (i - gap_start > bestgap_l): 
                    bestgap_start = gap_start
                    bestgap_end = i - 1
                    bestgap_l = bestgap_end - bestgap_start + 1
                gap_start = -1
                
        else:
            glyphs[si] = oldglyphs['32']
            if gap_start == -1:
                # start of gap
                gap_start = i

    if (bestgap_l > 0): 
        for i in range(bestgap_start,bestgap_end+1):
            del glyphs[str(i)]
        encoding_start1 = abs_min_ch
        encoding_end1 = bestgap_start - 1
        encoding_start2 = bestgap_end + 1
        encoding_end2 = abs_max_ch
    else:
        encoding_start1 = abs_min_ch
        encoding_end1 = abs_max_ch
        encoding_start2 = 0
        encoding_end_2 = 0

    #print('start1 : ',encoding_start1) 
    #print('end1 : ',encoding_end1) 
    #print('start2 : ',encoding_start2) 
    #print('end2 : ',encoding_end2) 

    # Compute_min_max
    max_width=0
    max_height=0
    max_delta=0
    min_xoffset=0
    max_xoffset=0
    min_yoffset=0
    max_yoffset=0
    for glyph in glyphs.values():
        #if glyph['encoding'] == 0: glyph['encoding'] = index of loop; ???
        if (glyph['width'] > max_width): max_width = glyph['width']
        if (glyph['height'] > max_height): max_height = glyph['height']
        if (glyph['xoffset'] < min_xoffset): min_xoffset = glyph['xoffset']
        if (glyph['xoffset'] > max_xoffset): max_xoffset = glyph['xoffset']
        if (glyph['yoffset'] < min_yoffset): min_yoffset = glyph['yoffset']
        if (glyph['yoffset'] > max_yoffset): max_yoffset = glyph['yoffset']
        if (glyph['delta'] > max_delta): max_delta = glyph['delta']

    bits_width =   bits_required_unsigned(max_width)
    bits_height =  bits_required_unsigned(max_height)
    bits_xoffset = bits_required_signed(min_xoffset, max_xoffset)
    bits_yoffset = bits_required_signed(min_yoffset, max_yoffset)
    bits_delta =   bits_required_unsigned(max_delta)

    # internal font name
    font_name = font_name+str(font_size);
    if is_bold: font_name += '_Bold'
    if is_italic: font_name += '_Italic'


    # output the glyph data
    outstr += '\n\nstatic const unsigned char '+fontname+'_data[] PROGMEM = {\n'
    for glyph in glyphs.values():
        glyph['byteoffset'] = output_state_bytecount
        output_glyph(glyph)
    output_newline();
    outstr = outstr[:-2]+' };\n'
    datasize = output_state_bytecount
    outstr += '/* font data size: '+str(datasize)+' bytes */\n\n'
    bits_index = bits_required_unsigned(output_state_bytecount)

    # output the index
    outstr += 'static const unsigned char '+fontname+'_index[] PROGMEM = {\n'
    for glyph in glyphs.values():
        output_number(glyph['byteoffset'], bits_index)
    output_pad_to_byte()
    output_newline()
    outstr = outstr[:-2]+' };\n'
    indexsize = output_state_bytecount - datasize
    outstr += '/* font index size: '+str(indexsize)+' bytes */\n\n'

    # output font structure
    outstr += 'const ILI9341_t3_font_t '+fontname+' PROGMEM = {\n'
    outstr += '\t'+fontname+'_index,\n'
    outstr += '\t0,\n'
    outstr += '\t'+fontname+'_data,\n'
    if bits_per_pixel > 1:
        outstr += '\t23,\n'                             # version 2.3
        outstr += '\t'+str(bpp_index)+',\n'             # lower 2 bits of reserved byte indicate bpp
    else:
        outstr += '\t1,\n'  # version 1
        outstr += '\t0,\n'  # reserved byte empty
    outstr += '\t'+str(encoding_start1)+',\n'
    outstr += '\t'+str(encoding_end1)+',\n'
    outstr += '\t'+str(encoding_start2)+',\n'
    outstr += '\t'+str(encoding_end2)+',\n'
    outstr += '\t'+str(bits_index)+',\n'
    outstr += '\t'+str(bits_width)+',\n'
    outstr += '\t'+str(bits_height)+',\n'
    outstr += '\t'+str(bits_xoffset)+',\n'
    outstr += '\t'+str(bits_yoffset)+',\n'
    outstr += '\t'+str(bits_delta)+',\n'
    outstr += '\t'+str(line_space)+',\n'
    outstr += '\t'+str(cap_height)+'\n'
    outstr += '};\n\n'

    # Message
    print('  Processed',str(len(glyphs.values())),'glyphs. Index is',str(indexsize),'bytes. Data is',str(datasize),'bytes.')
    return outstr



# Return the name of the font and the fontsize associated with a filename
def parseFilename(filename, lite):
    name = filename.replace("-","_")    
    name = name.replace("_Regular","")
    pp = name[:-4].rsplit('_',1)
    q = pp[1].split("@")
    aa = 1
    pt = q[0]
    if (len(q) > 1): aa = int(q[1])     
    name = pp[0]
    if (aa > 1) : name += '_AA' + str(aa)
    name += lite
    return "font_" + name, pt



def makecpp(src_prefix, dst_prefix, fname, flist, rangemin,rangemax, lite):

    fname += lite
    print("\n\n********************************************\nFONT NAME: ", fname, "\n********************************************\n"); 
    headername = "_ILI9341_t3_" + fname + "_H_"
    hfile  = "#ifndef " + headername + "\n#define " + headername + "\n\n"
    hfile += '''#include "tgx.h"
    
//#ifdef __cplusplus
//extern "C" {
//#endif


'''

    for pt, filename in flist:
        hfile += "extern const ILI9341_t3_font_t " + fname + "_" + str(pt)  + ";\n"
    hfile += '''


//#ifdef __cplusplus
//} // extern "C"
//#endif

#endif
'''

    outfile = open(dst_prefix + fname + ".h", 'w')
    outfile.write(hfile)
    outfile.close()
        
    cfile = '#include "' + fname + '.h"\n\n' 
    for pt , filename in flist:
        print("\n----->", pt , "points")
        cfile += dofile(src_prefix + filename, fname + "_" + str(pt), rangemin, rangemax)
        
    cfile += "// end of file \n\n"
    outfile = open(dst_prefix + fname + ".cpp", 'w')
    outfile.write(cfile)
    outfile.close()





# get a list of all bdf files
src_path_prefix = "../bdf/"
dst_path_prefix = "../src/"
ttf_path_prefix = "../ttf/used/"
preview_name = "../font-list.html"


files = [f for f in listdir(src_path_prefix) if f.endswith('.bdf') and isfile(src_path_prefix + f)]


# create a dictionnary with key = font name and values a list of pair (filename, pt)
fontdic = {}
for f in files:
    name, pt = parseFilename(f, "")
    if name not in fontdic:
        fontdic[name] = [(pt, f)]
    else:
        fontdic[name].append( (pt, f) )

# sort each list of fontsize by increasing font size
for fname in fontdic:
    fontdic[fname] = sorted(fontdic[fname], key=lambda x: x[0] )
    
# iterate over the fonts and create the files
for fname in fontdic.keys():
    makecpp(src_path_prefix, dst_path_prefix, fname, fontdic[fname], 32,255, "")
    makecpp(src_path_prefix, dst_path_prefix, fname, fontdic[fname], 32,126, "_lite")

#create the preview
print("\n\n\nCreating preview of fonts\n\n")
# get a list of ttf files with their name
ttffiles = [f for f in listdir(ttf_path_prefix) if f.lower().endswith('.ttf') and isfile(ttf_path_prefix + f)]
listtf = []
for f in ttffiles:
    name = f[:-4].replace("-", "_"); 
    name = name.replace("_Regular","")
    listtf += [(name, f)]

hstr = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>tgx-font list</title>
<style>
"""

for name, filename in listtf:
    hstr+= '@font-face { font-family:' + name + '; src:url("./ttf/used/' + filename + '");}\n'
    
hstr += """

h1 {font-size: xx-large}
h2 {font-size: xx-large; color: green;}

</style>
</head>
<body>
<h1 style="text-align:center">tgx-font list</h1>
"""
    
for name, filename in listtf:
    hstr+=f"""
        
<div style="background-color:lightyellow;border: 5px solid black;padding: 5px;margin: 5px;">
<h2>Font {name}</h2>
<div style="font-family: {name};">
<p style="font-size:x-large">1234567890<br>=+-/*;,.!?&lt;&gt;#~@<br>abcdefghijklmnopqrstuvwxyz<br>ABCDEFGHIJKLMNOPQRSTUVWXYZ</p>
<p style="font-size:xx-large;">The quick brown fox jumps over the lazy dog.</p>
</div></div>    
"""

hstr+= """

</body>
</html>

"""

outfile = open(preview_name, 'w')
outfile.write(hstr)
outfile.close()
