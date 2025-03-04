import sys, csv

FLOW_TYPES = {
    'TypeI'   : "/power/typeI/",
    'TypeII'   : "/power/typeII/",
    'BE'   : "/power/be/"
}

def gettype(name):
    for k, v in FLOW_TYPES.items():
        if name.startswith(v):
            return k
    raise Exception("Unclassified name: '%s'" % name)

def main(infile):

    latlog = open("lat_%s" % infile, "w")
    latlog.write("srcid dstid timesent timerecv latency flowcls pktname\n")

    fh = open(infile)
    reader = csv.reader(fh, delimiter=',', skipinitialspace=True)
    reader.next() # skip header
    
    deliveredCount = {x: 0 for x in FLOW_TYPES}
    deliveredSize  = {x: 0 for x in FLOW_TYPES}
    
    outstanding = {}
    agg_queue = {}
    agg_tmp = {}
    count = 0
    list_processed = {}
    list_wacflows = []
    list_pdcflows = []
    list_bgdflows = []
    for nodeid, event, name, payloadsize, time in reader:
    
        nodeid = int(nodeid)
        payloadsize = int(payloadsize)
        time = float(time)
        cls = gettype(name)
        
        if event == "sent":
            
            # pub-sub flow needs different handling due to multisource multicast
            if cls == "DATA":# or  cls == "BGD":
                outstanding[name] = (time, payloadsize, 1)
                print(outstanding[name])
	    #elif cls == "BGD":
	    	#pass
            else:
                if name in outstanding:
                    print(name)
                    print(time)
                    #(t1, ps1, c1) = outstanding[name]
                    #if t1 != time:
                    #    raise Exception("Duplicate outstanding with mismatched timestamp")
                    #outstanding[name] = (t1, ps1 + payloadsize, c1 + 1)
                    raise Exception("whoa dupe")
                else:
                    outstanding[name] = (time, payloadsize, 1, nodeid, name)
            if cls in ["PMU_COM", "AMI_COM"]:
                agg_tmp[name] = agg_queue[(nodeid, cls[:3])]
                agg_queue[(nodeid, cls)] = []
            
        elif event == "recv":
	    if name in outstanding:
            	t1, ps1, c1, sn1, pktname = outstanding[name]
	    else:
		continue

            # don't remove outstanding pub-sub entry, it can be delivered multiple times
            if cls != "DATA":
		pass #single interest packet can be delivered multiple times
                #if c1 == 1:
                    #del outstanding[name]
                #else:
                    #raise Exception("ddd")
                    #outstanding[name] = (t1, ps1 - payloadsize, c1 - 1)
            
            latency = time - t1
            deliveredCount[cls] += 1
            deliveredSize[cls]  += ps1

            latlog.write("%d %d %.9f %.9f %.9f %s %s\n" % (sn1, nodeid, t1, time, latency, cls, name))
            if name not in list_processed:
                list_processed[name] = []
	    list_processed[name].append(str(sn1) + " " + str(nodeid) + " " + str(t1) + " " + str(time) + " " + str(latency) + " " + str(cls) + " " + str(name))
            if cls in ["PMU_AGG", "AMI_AGG"]:
                if not (nodeid, cls) in agg_queue:
                    agg_queue[(nodeid, cls[:3])] = []
                agg_queue[(nodeid, cls[:3])].append(latency)
            
            if cls in ["PMU_COM", "AMI_COM"]:
                for agglat in agg_tmp[name]:
                    latlog.write("%s %.6f\n" % (cls[:3]+ "_TOT", latency + agglat))

    #latlog.close()

    
    #Save all the flows
    with open("ndn_all_flows.csv") as flowfile:
        for line in flowfile:
                flowsplit = line.strip().split()
                if flowsplit[2] == "TypeII":
                        list_wacflows.append(line.strip())
                if flowsplit[2] == "TypeI":
                        list_pdcflows.append(line.strip())
                if flowsplit[2] == "BE":
                        list_bgdflows.append(line.strip())
        

    flowcompleted = False
    infinitelat = 400
    outcounter = 0

    #Process each interest sent according to flow
    for name in outstanding:

	outcounter += 1
        if(outcounter % 100 == 0):
	    print "Processing packet...", outcounter, "out of", len(outstanding)

        if "typeII" in name:
                #Check all WAC flows
                wacsrcnode = outstanding[name][3]
		wacsrctime = outstanding[name][0]
		wacpktname = outstanding[name][4]

                for wflow in list_wacflows:
                        flowcompleted = False
                        #If flow exists, check if entry is in the processed list
                        if int(wacsrcnode) == int(wflow.split(" ")[1]):
                                if name in list_processed:
                                   #Verify if flow exist in processed file or not
                                   for procd in list_processed[name]:
                                        procditem = procd.split()
                                        if (int(wacsrcnode) == int(procditem[0])) and (int(wflow.split(" ")[0]) == int(procditem[1])) and (wacpktname.strip() == procditem[6].strip()):
                                                #print "Processing packet loss...WAC flow completed"
						flowcompleted = True
                                                break
                                if flowcompleted == False:
                                        #print wacsrcnode, wflow.split(" ")[0], outstanding[name][4], "WAC packet loss!!!"
					latlog.write("%d %d %.9f %.9f %.9f %s %s\n" % (int(wacsrcnode), int(wflow.split(" ")[0]), float(wacsrctime), infinitelat, infinitelat - float(wacsrctime) , "TypeII", wacpktname))

        if "typeI/" in name:
                #Check all PDC flows
                pdcsrcnode = outstanding[name][3]
                pdcsrctime = outstanding[name][0]
		pdcpktname = outstanding[name][4]

                for pflow in list_pdcflows:
                        flowcompleted = False
                        #If flow exists, check if entry is in the processed list
                        if int(pdcsrcnode) == int(pflow.split(" ")[1]):
                                if name in list_processed:
                                   #Verify if flow exist in processed file or not
                                   for procd in list_processed[name]:
                                        procditem = procd.split()
                                        if (int(pdcsrcnode) == int(procditem[0])) and (int(pflow.split(" ")[0]) == int(procditem[1])) and (pdcpktname.strip() == procditem[6].strip()):
                                                #print "Processing packet loss...PDC flow completed"
						flowcompleted = True
                                                break
                                if flowcompleted == False:
                                        #print pdcsrcnode, pflow.split(" ")[0], outstanding[name][4], "PDC packet loss!!!"
                                        latlog.write("%d %d %.9f %.9f %.9f %s %s\n" % (int(pdcsrcnode), int(pflow.split(" ")[0]), float(pdcsrctime), infinitelat, infinitelat - float(pdcsrctime) , "TypeI", pdcpktname))


        if "be" in name:
                #Check all PDC flows
                bgdsrcnode = outstanding[name][3]
                bgdsrctime = outstanding[name][0]
                bgdpktname = outstanding[name][4]

                for bflow in list_bgdflows:
                        flowcompleted = False
                        #If flow exists, check if entry is in the processed list
                        if int(bgdsrcnode) == int(bflow.split(" ")[1]):
                                #Verify if flow exist in processed file or not
                                for procd in list_processed[bgdsrcnode]:
                                        procditem = procd.split()
                                        if (int(bgdsrcnode) == int(procditem[0])) and (int(bflow.split(" ")[0]) == int(procditem[1])) and (bgdpktname.strip() == procditem[6].strip()):
                                                #print "Processing packet loss...PDC flow completed"
                                                flowcompleted = True
                                                break
                                if flowcompleted == False:
                                        #print bgdsrcnode, bflow.split(" ")[0], outstanding[name][4], "BGD packet loss!!!"
                                        latlog.write("%d %d %.9f %.9f %.9f %s %s\n" % (int(bgdsrcnode), int(bflow.split(" ")[0]), float(bgdsrctime), infinitelat, infinitelat - float(bgdsrctime) , "BE", bgdpktname))
    
    lostCount = {x: 0 for x in FLOW_TYPES}
    lostSize  = {x: 0 for x in FLOW_TYPES}

    metlog = open("met_%s" % infile, "w")
    metlog.write("flowcls recvcnt recvsize losscnt losssize\n")

    #for name, (time, payloadsize, count) in outstanding.items():
        #cls = gettype(name)
        #if cls != "DATA":
            #lostCount[cls] += 1
            #lostSize[cls]  += payloadsize

    #Declare variables to store PMU and AMI total bytes transmitted
    totalLossPMU = 0
    totalRecvPMU = 0
    totalLossAMI = 0
    totalRecvAMI = 0
    totalLossCntPMU = 0
    totalRecvCntPMU = 0
    totalLossCntAMI = 0
    totalRecvCntAMI = 0

    for cls in FLOW_TYPES:
	#Calculate total received and lost bytes (PMU and AMI)
	if cls == "PMU_AGG":
		totalLossPMU += lostSize[cls]
	if cls == "PMU_COM":
		totalLossPMU += lostSize[cls]
		totalRecvPMU += deliveredSize[cls]
                totalLossCntPMU += lostCount[cls]
		totalRecvCntPMU += deliveredCount[cls]
	if cls == "AMI_AGG":
                totalLossAMI += lostSize[cls]
        if cls == "AMI_COM":
                totalLossAMI += lostSize[cls]
                totalRecvAMI += deliveredSize[cls]
		totalLossCntAMI += lostCount[cls]
                totalRecvCntAMI += deliveredCount[cls]

        metlog.write("%s %d %d %d %d\n" % (cls, deliveredCount[cls], deliveredSize[cls], lostCount[cls], lostSize[cls]))
    
    #Write total values received at compute layer to processed file (PMU and AMI)
    metlog.write("%s %d %d %d %d\n" % ("PMU_TOT", totalRecvCntPMU, totalRecvPMU, totalLossCntPMU, totalLossPMU))
    metlog.write("%s %d %d %d %d\n" % ("AMI_TOT", totalRecvCntAMI, totalRecvAMI, totalLossCntAMI, totalLossAMI))

    metlog.close()
    fh.close()

    #add loss packets to the latency file, with very high values (infinity)
    metlognew = open("met_%s" % infile, "r")
    for line in metlognew:
	linevalues = line.split(" ")
	if linevalues[0] == "ERROR":
		for i in range(int(linevalues[3])):
			latlog.write("%s %0.6f\n" % ("ERROR", 0.100000))
	if linevalues[0] == "DATA":
                for i in range(int(linevalues[3])):
                        latlog.write("%s %0.6f\n" % ("DATA", 0.100000))
	if linevalues[0] == "PMU_TOT":
                for i in range(int(linevalues[3])):
                        latlog.write("%s %0.6f\n" % ("PMU_TOT", 0.100000))
	if linevalues[0] == "AMI_TOT":
                for i in range(int(linevalues[3])):
                        latlog.write("%s %0.6f\n" % ("AMI_TOT", 0.100000))

    metlognew.close()
    latlog.close()

    return 0

if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
