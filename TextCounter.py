import os
import csv

def parse_int_txt_line(line):           #The first to funct 
    res = []                            #breaks the line to substrings
    parts = line.split('\n')
    for i in range(len(parts)):
        res.append(str(parts[i]))
    return res

def wordsPerLine(path):  #reads and creates a list out of the text by row
    result = []   #2 dim list that breaks the text into sub-lists in each line
    first_line = True
    f = open(path)
    for line in f:
        if (first_line):
            result.append(line.rstrip().split("\n"))
            first_line = False
        else: 
            result.append(parse_int_txt_line(line.rstrip()))
    f.close()
    row = []             #one dim list that represents the number of words in each line 
    for i in range(len(result)):
        row_count = len(result[i][0].split())
        row.append(row_count)
    return row
        
def countWord(path):
    searchedWord="Dorian"
    file = open(path, "r")
    stri= ""                    #create empty string to manipulate data
    for line in file:
        stri+=line
    word_stri = stri.split()    #split the string and convert it into list
    file.close()
    count = 0
    for i in range(len(word_stri)):  #checks each line and looks for the word we are trying to find
        if word_stri[i][:6] == searchedWord:
            count += 1
        if word_stri[i][1:7] == searchedWord:
            count += 1
    return (count)      #returns the ammount of times dorian existed in the whole text
        
def save_output(output,name_count):
    f = open("output.txt", 'w')         #opens a new txt file and writes to it
    for i in range(len(output)):        #runs on the given list and prints the quantities of words in each line
        item = str(output[i]) + "\n"    
        f.write(item)
    f.write(" The number of times the word 'Dorian' appeared is: "+ str(name_count))
    f.close()
        
    return () 

def main():  
    try:
        nameCounter = countWord("our_input.txt") #variable gets the quantity of Dorians in each line  
        ListofQuant = wordsPerLine("our_input.txt")  #counts words in each line of text and creats a long list that describes it 
        save_output(ListofQuant,nameCounter)   #a function that saves the results in an output txt file  
        print("output file successfully created!")
    except:
        print("\n \t *** Error -Could not open the file ***")
        print(" \n \tPlease change source file name to: 'our_input.txt' ") 
main()
