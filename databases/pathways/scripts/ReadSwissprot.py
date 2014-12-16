#!/usr/bin/env python
from cStringIO import StringIO
import sys,string
import sys, os
import argparse
import tempfile



#********************************************************************************************
#    Read Swissprot program                                                                 *
#    This program reads the unprot.dat file and creates an                                  *
#    extract containing in each line                                                        *
#    The Protein AC and all the ECs related to it                                           *

#  -----------------------------------------------------------------------------------------*
#  Invoking the program:  (Using the current location of the files)                         *
#  ---------------------                                                                    *
#   python ReadSwissprot.py  --i  /n/huttenhower_lab/data/uniprot/2014-09/uniprot_sprot.dat\
#   --o output_file \                          
#   --uniref50gz /n/huttenhower_lab/data/idmapping/map_uniprot_UniRef50.dat.gz\
#   --uniref90gz /n/huttenhower_lab/data/idmapping/map_uniprot_UniRef90.dat.gz 
#                                                                                           *
#   Where:                                                                                  *
#   --i input_file is the UniprotKB Swissprot text file, which can be downloaded from       *
#    ftp://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.dat.gz *
#                                                                                           *
#   The current downloaded file, which serves as input,  resides on hutlab3 in              *
#    /n/huttenhower_lab/data/uniprot/2014-09/uniprot_sprot.dat                              *
#                                                                                           *
#                                                                                           *
#   Written by George Weingart - george.weingart@gmail.com   10/06/2014                     *  
#                                                                                           *
#   MODIFICATION LOG   12/15/2014 george.weingart@gmail.com                                 *
#   ----------------                                                                        *
#   Modifying the code so that it creates an extract in the form AC,EC(S),U50,U90           *
#   For that, we have to read and unpack the U50 and U90 files,  paste them together        *
#   and for each AC that has an EC, retrieve the corresponding U50 and U90                  *
#                                                                                           *
#********************************************************************************************








#*************************************************************************************
#* Read Swissprot                                                                    *
#* Each AC that has an AC is loaded into the table of ACs so that afterwards         *
#*    we retrieve its corresponding U50 and U90                                      *
#*************************************************************************************
def ReadSwissprot(CommonArea):
	dAC = dict()
	iFile =CommonArea['iFile']
	strTab = "\t"
	strNewLine = "\n"
	bFlagEC = False
	lECs = list()
	InputFile = open(iFile)
	LineCntr = 0
	ACsPostedCounter = 0
	for iLine in InputFile: 
			LineCntr = LineCntr +1
			if iLine.startswith("AC   "):
				lTemp = iLine.rstrip().split().pop().split(";")
				lACs = [var for var in lTemp if var]
  
			if iLine.startswith("DE   ") and "EC=" in iLine:
				bFlagEC = True
				iLine1 = iLine.replace(";"," ")
				iECLoc = iLine1.find("EC=") + 3
				EC = iLine1[iECLoc:].split(" ")[0]
				EC  =  EC.replace("EC=","")
				EC  =  EC.replace(".-","")
				lECs.append(EC)
 
			if  bFlagEC == True and iLine.startswith("//"):
				   for ProtAC in lACs:
						dAC[ProtAC] = dict()			#For each AC we build a Dictionary
						dAC[ProtAC]['ECs'] = lECs		#And post the ECs - later we will post the U50 and U90
						ACsPostedCounter = ACsPostedCounter + 1
				   bFlagEC = False
				   lECs = list()
				   lACs = list() 
	
	print "Read " + str(LineCntr) + " Input Lines from the Swissprot text file"
	print "Loaded  " + str(ACsPostedCounter) + " ACs into the AC table"
	CommonArea['dAC'] = dAC
	InputFile.close()
 	return CommonArea











#*************************************************************************************
#* Parse Input parms                                                                 *
#*************************************************************************************
def read_params(x):
	CommonArea = dict()	
	parser = argparse.ArgumentParser(description='Read Swissprot and generate an exract with AC and all ECs related to it')
	parser.add_argument('--i', action="store", dest='i',nargs='?')
	parser.add_argument('--o', action="store", dest='o',nargs='?',  default='output_analysis')
	parser.add_argument('--uniref50gz', action="store", dest='Uniref50gz',nargs='?')
	parser.add_argument('--uniref90gz', action="store", dest='Uniref90gz',nargs='?')
	CommonArea['parser'] = parser
	return  CommonArea




#********************************************************************************************
#*   Initialize the process of building the Uniref5090 files                                *
#********************************************************************************************
def InitializeProcess(strUniref50gz,  strUniref90gz):

	dInputFiles = dict()									# Initialize the dictionary
	dInputFiles["Uniref50gz"] = strUniref50gz				# Store 1st file name in dictionary
	dInputFiles["Uniref90gz"] = strUniref90gz				# Store 2nd file name in dictionary

	strTempDir = tempfile.mkdtemp()							# Make temporary folder to work in
	dInputFiles["TempDirName"] = strTempDir					# Store the name of the temp dir for future use
	cmd_chmod = "chmod 755 /" + strTempDir					# Change permissions to make usable 
	os.system(cmd_chmod)									# Invoke os
	strUniref50gzFileName = os.path.split(strUniref50gz)[1]
	strUniref90gzFileName = os.path.split(strUniref90gz)[1]
	print "Unzipping uniref50 file"
	cmd_gunzip = "gunzip -c " + strUniref50gz + ">" + strTempDir + "/" + strUniref50gzFileName[:-3] # Build the gunzip command
	os.system(cmd_gunzip)									# Invoke os
	print "Unzipping uniref90 file"
 	cmd_gunzip = "gunzip -c " + strUniref90gz + ">" + strTempDir + "/" + strUniref90gzFileName[:-3] # Build the gunzip command
	os.system(cmd_gunzip)									# Invoke os
	print "Pasting Uniref50 to Uniref90"

	cmd_paste =  "paste " +  strTempDir + "/" + strUniref50gzFileName[:-3] + " " +\
						strTempDir + "/" + strUniref90gzFileName[:-3] + ">" +\
						strTempDir + "/" + strUniref50gzFileName[:-7] +  "90"    # Paste the two files together
	os.system(cmd_paste )									# Invoke os
	dInputFiles["File5090"] = strTempDir + "/" + strUniref50gzFileName[:-7] +  "90"  #Post the file created into the Common Area
	return dInputFiles


	
	
#**************************************************************
#*           Match Txn vs Master                              *
#**************************************************************
def TxnVsMaster(CommonArea):
	dUniprotUniref = dict()
	FlagEnd = False
	iTxnIndex = 0	
	iTotalACsProcessed = 0	
	iPrintAfterACReads = 1000   							# Print status after processing this number of ACs	
	iTotalUniref5090RecsRead = 0							# Counter of Uniref5090 recs Read
	iPrintAfterReads = 1000000 								# Print status after read of these number of records
	
	
	lACs = list()
	for AC in CommonArea['dAC'].iterkeys():
		lACs.append(AC) 
	CommonArea['lACsSorted'] = sorted(lACs)
 	CommonArea['File5090'] = open(CommonArea['strInput5090'])							# Open the file
	MasterLine = CommonArea['File5090'].readline()						# Read the Line
	MKey = MasterLine.split()[0]							# This is the Master Key
	TxnKey = CommonArea['lACsSorted'][0]
	

	while  FlagEnd == False:
		if MKey == TxnKey:
			iTxnIndex = iTxnIndex + 1
			if iTxnIndex >=  len(CommonArea['lACsSorted']) - 1:
				FlagEnd = True
			iTotalACsProcessed+=1							# Count the reads
			if  iTotalACsProcessed %  iPrintAfterACReads == 0:	# If we need to print status
				print "Total of ", iTotalACsProcessed, " ACs Processed against the Uniref5090 file"	
			TxnKey = CommonArea['lACsSorted'][iTxnIndex]
			lInputLineSplit = MasterLine.split() 				# Split the line using space as delimiter
			lEnt5090 = list()									# Initialize list
			lEnt5090.append(lInputLineSplit[1].split("_")[1])	# Entry is of the form UniRef50_Q2FWP1 - We need only the Q2FWP1
			lEnt5090.append(lInputLineSplit[3].split("_")[1])	# Entry is of the form UniRef50_Q2FWP1 - We need only the Q2FWP1
			dUniprotUniref[lInputLineSplit[0]] = lEnt5090		# Post it in the dictionary
			continue
		elif  TxnKey > MKey:
			MasterLine = CommonArea['File5090'].readline() 
			if not MasterLine: 
				FlagEnd = True
			iTotalUniref5090RecsRead+=1							# Count the reads
			if  iTotalUniref5090RecsRead %  iPrintAfterReads == 0:	# If we need to print status
				print "Total of ", iTotalUniref5090RecsRead, " Uniref5090 records read"
			MKey = MasterLine.split()[0]
			continue
		elif  TxnKey < MKey:
			iTxnIndex = iTxnIndex + 1
			if iTxnIndex >=  len(CommonArea['lACsSorted']) -1:
				FlagEnd = True
			TxnKey = CommonArea['lACsSorted'][iTxnIndex]
			iTotalACsProcessed+=1							# Count the reads
			if  iTotalACsProcessed %  iPrintAfterACReads == 0:	# If we need to print status
				print "Total of ", iTotalACsProcessed, " ACs Processed against the Uniref5090 file"	
			continue
			
	CommonArea['dUniprotUniref'] = dUniprotUniref
	return CommonArea

#**************************************************************
#*      Build the Output file                                 *
#**************************************************************	
def  GenerateOutputFile(CommonArea):
	strTab = "\t"
	strNewLine = "\n"
	OutputLineCntr = 0
	OutputFile = open(CommonArea['oFile'],'w')
	for AC in sorted(CommonArea['dAC'].keys()):
		lOutputRecord = [AC]
		try:
			for EC in CommonArea['dAC'][AC]['ECs']:
				lOutputRecord.append(EC)
			U50 = "Uniref50_" + CommonArea['dUniprotUniref'][AC][0]
			U90 = "Uniref90_" + CommonArea['dUniprotUniref'][AC][1]
			lOutputRecord.append(U50)
			lOutputRecord.append(U90)
			strBuiltRecord = strTab.join(lOutputRecord) +  strNewLine
			OutputFile.write(strBuiltRecord)
			OutputLineCntr = OutputLineCntr + 1
		except:
			pass
	
	OutputFile.close()
	print "Total number of AC,EC(s), Uniref_50,Uniref_90 records generated is: ", str(OutputLineCntr),"\n"
	return CommonArea

#*************************************************************************************
#*  Main Program                                                                     *
#*************************************************************************************
print "Program started"
CommonArea = read_params( sys.argv )  # Parse command  
parser = CommonArea['parser'] 
results = parser.parse_args()

CommonArea['iFile'] = results.i
CommonArea['oFile'] = results.o
CommonArea = ReadSwissprot(CommonArea)			#Read Swissprot and resolve the relation AC --> EC{s}

strUniref50gz = results.Uniref50gz					# The first file is the zipped version of the Uniref50 Translation file
strUniref90gz = results.Uniref90gz					# The 2nd file is the zipped version of the Uniref90 Translation file
dInputFiles =  InitializeProcess(strUniref50gz,  strUniref90gz)  # Build the Uniref5090 files
CommonArea['strInput5090'] = dInputFiles["File5090"]		#Name of the Uniref5090 file
print "After building the Uniref5090 files"

CommonArea = TxnVsMaster(CommonArea)   #Process the 5090 file against the ACs
cmd_remove_tempdir = "rm -r /" + dInputFiles["TempDirName"]		# Remove the temporary directory
os.system(cmd_remove_tempdir)

CommonArea = GenerateOutputFile(CommonArea)			#Build the OutputFile


print "Program ended Successfully"
exit(0)
