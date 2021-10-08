#include <iostream>
#include <fstream>

#include <cstdio>

#include "TNtuple.h"
#include "TH1F.h"
#include "TH2F.h"
#include "TCanvas.h"
#include "TStyle.h"
#include "TPad.h"

int getFileSize(std::ifstream& f);

using namespace std;

void plot_event_fphx1_and_2(char* fname = "data_0", int maxbuf=0, int n_meas = 64, float maxscale = 200.)
{
	gStyle->SetOptFit(1);
	gStyle->SetOptStat(0);
	unsigned long int dataIn[1000000];

	int bco, adc, ampl, chip_id, mchip, module, fpga_id, chipside, side, bco128;
	int chan_id;

        //float adcconv[8] = {2000, 4000, 8000, 12000, 20000, 28000, 36000, 44000};
        float adcconv[8] = {3375, 4000, 8000, 12000, 20000, 28000, 36000, 44000};
        float charge;

	int NCHAN = 128;

	TNtuple *hits = new TNtuple("hits","test","chan_id:ampl:adc:bco:rawchip:event:fpga:module:chip:side:charge:file_event");
	TNtuple *event = new TNtuple("event","test","event:nhits:nclus:cluswid1:cluswid2:cluswid3:cluswid4:adctot1:adctot2:adctot3:adctot4:module1:chip1:chan1:module2:chip2:chan2:module3:chip3:chan3:module4:chip4:chan4:side1:side2:side3:side4:charge1:charge2:charge3:charge4:nclus1:nclus2:nclus3:nclus4:pos1:pos2:pos3:pos4:nmod:spos1:spos2:spos3:spos4");
	TNtuple *cluster = new TNtuple("cluster","","event:module:side:chip:chan1:cluswid:adctot:bco:nclus:charge:pos:charge1:charge2:charge3:charge4");
	TNtuple *track = new TNtuple("track","","event:nhits:pos1:pos2:pos3:pos4:nhitse:side1:side2:side3:side4");

	std::ifstream f(fname,std::ifstream::binary);

	if ( ! f.is_open() )
	{
		std::cout << "Failed to open input file " << fname << std::endl;
		return;
	}

	// get size of file
	int size = getFileSize(f);
	std::cout << "Input file " << fname << std::endl;
	std::cout << "Number of bytes in file = " << size << std::endl;

	// Brute force approach: allocate a single array to hold the entire
	// contents of the file
	unsigned int* data = new unsigned int[size/sizeof(unsigned int)];

	f.read((char*)data,size);
	if ( f.fail() )
	{
		std::cout << "eof, fail, or bad condition during read" << std::endl; 
		delete [] data;
		return;
	}

	// Counter to count the number of hits for each channel and amplitude:
	int nhits[128][1024];

	for (int ichan=0; ichan<NCHAN; ichan++)
		for (int iamp = 0; iamp < n_meas; iamp ++) nhits[chan_id][iamp] = 0;

	// Extract bco, channel, amplitude, and adc from each hit, and count the number of 
	// hits at each amplitude for each channel:

	int ievent = 0;
	int hitevent = 0;
	int bufcnt = 0;

	//   while (ievent < 100)

	int bcolast = -999;
	int nhitsevent[4][8] = {0};
	bool firstevent = true;
	int adctot[4][8][128] = {0};         // total adc value of each cluster found in a module, chip
	float chargetot[4][8][128] = {0};    // total charge of each cluster found in a module, chip
	float chargehit[4][8][128][4] = {0};    // total charge of each cluster found in a module, chip
	float cluspos[4][8][128] = {0};      // centroid of cluster, calculated by center of gravity
	int chanhits[4][8][128] = {999};
	int adchits[4][8][128] = {999};
	int usedhit[4][8][128] = {0};
	int ichiplast[4] = {999};

	for (int index=0; index<size/sizeof(unsigned int); bufcnt++)
	{
		if ( maxbuf && bufcnt >= maxbuf ) break;
#ifdef OLD
		// Get record size
		int start = index;
		int cnt = data[start];
		// Unpack the record
		int word1 = data[start+1];
		int word2 = data[start+2];
#else
		int buflen = data[index];
		int bufid = data[index+1];
		int cnt = buflen - 1;
		int start = index+2;
		//std::cout << buflen << " " << bufid << " " << cnt << std::endl;

		// Fake the old fmt logic
		int word1 = 0xFFFFFFFF;
		int word2 = 0xFFFFFFFF;
		if ( bufid == 100 ) word1 = 100;
		if ( bufid == 101 ) { word1 = 0xFFFFFFFF; word2 = 0xFFFFFFFF; }
		if ( bufid == 102 ) word1 = 102;
#endif
		if ( word1 == 0xFFFFFFFF && word2 == 0xFFFFFFFF )
		{
			if ( bufid == 101 )
			{
				// This record is a time stamp
				// Format of timestamp record is
				//   data[0] = word count, excluding this word and checksum
				//   data[1] = 0xFFFFFFFF
				//   data[2] = 0xFFFFFFFF
				//   data[3] = time in clock ticks for cpu
				//   data[4] = CLOCKS_PER_SEC taken from the system value
				//   data[5] = checksum for buffer
				std::cout << "Buffer " << bufcnt << ": Timestamp" << std::endl;
#ifdef OLD
				index = start + cnt + 2;
#else
				index = start + cnt;
#endif
				//index = start + cnt + 2;
				continue;
			}
		}
		else if ( word1 == 100 )
		{
			// This buffer is a configuration record
			std::cout << "Buffer " << bufcnt << ": Configuration " << std::endl;
			index += 2;
			int runno = data[index++];
			std::cout << "    Run " << runno << std::endl;
			unsigned short* p = (unsigned short*)&data[index];
			for ( int n=0; n<9; )
			{
				unsigned short chipid = p[n++];
				unsigned short masks[8];
				for(int m=0; m<8; m++, n++) masks[m] = p[n];
				std::cout << "    Chip " << chipid << std::endl;
				std::cout << "      enable masks ";
				for(int m=0; m<8; m++) std::cout << "0x" << std::hex << masks[m] << " ";
				std::cout << std::dec << std::endl;
			}
			//unsigned char* p2 = &p[n];
			//for(int n=0; n<16; n++)
			//{
		        //		std::cout << "      Reg " << n << ": " << (int) p2[n] << std::endl;
			//}
#ifdef OLD
			index = start + cnt + 2;
#else
			index = start + cnt;
#endif
		}
		else
		{
			// Format of record is 
			//   data[0] = # of data words
			//   data[1..n] = data words
			//   data[n+1] = checksum for buffer
			std::cout << "Buffer " << bufcnt << ": Data record, "
				<< "nwords = " << cnt << " checksum = " 
				<< "0x" << std::hex << data[index+cnt+1] << std::dec << std::endl;
			int checksum = 0;

#ifdef OLD
			for ( index++; index<start+cnt+1; index++)
#else
			for (index+=2; index<start+cnt-1; index++)
#endif
			{
				if ( (index+1)*sizeof(unsigned int) > size )
				{
					// Safety belt against a partially-written buffer (it will have the full length
					// field, but the whole buffer hasn't been read in).  This can happen, for instance,
					// if we are reading a file that is actively being written.
					std::cout << "Partial buffer detected, bailing" << std::endl;
					break;
				}

				checksum ^= data[index];

				chip_id = (data[index]&0x7c)>>2;
				ampl = (data[index]&0x7e0000)>>17;
				fpga_id = (data[index]&0x80)>>7;

                                mchip = (chip_id < 9) ? chip_id : chip_id - 8;
                                if (fpga_id == 0) {
                                  module = (chip_id < 9) ? 0 : 1;
                                }
                                else{
                                  module = (chip_id<9) ? 3 : 2;
                                }

                                if (module < 3){		  
                                  //Decoding for FPHX-1:
                                  //DDDB BBBB BAAA AAA1 CCCC CCCX FIII II10
                                  // D = ADC, B = BCO, A = AMPLITUDE, C = CHAN_ID, F = FPGA_ID, I = CHIP_ID
                                  bco = (data[index]&0x1f800000)>>23;
                                  chan_id = (data[index]&0xfe00)>>9;
                                  adc = (data[index]&0xe0000000)>>29;
                                }
                                else{
                                  //Decoding for FPHX-2:
                                  // DDXB BBBB BAAA AAA1 CCCC CCBC FIII  IID0
                                  // D = ADC, B = BCO, A = AMPLITUDE, C = CHAN_ID, F = FPGA_ID, I = CHIP_ID
                                  bco128 = ((data[index] & 0x200) >> 3) | ((data[index] & 0x1f800000) >> 23);
                                  bco = (data[index] & 0x1f800000) >> 23;
                                  chan_id = ((data[index] & 0x100) >> 2) | ((data[index] & 0xfc00) >> 10);
                                  adc = ((data[index] & 0x2) << 1) | ((data[index] & 0xc0000000) >> 30);
                                }

                                if (adc < 7)charge = (adcconv[adc] + adcconv[adc+1])/2.0;
                                else charge = adcconv[adc];

				nhits[chan_id][ampl]++;
				if (ievent == 10) cout<<hex<<dataIn[ievent]<<" "<<chan_id<<" "<<bco<<" "<<ampl<<endl;


				bool foundhit = false;
				for (int ihit = 0; ihit < nhitsevent[module][mchip-1]-1; ihit++) if (chanhits[module][mchip-1][ihit] == chan_id) foundhit = true;

				// If this is the first hit or if this hit has the same bco as the last hit +/- 1
				// then this is a candidate hit to add to the current event:

				// Check to see if this module already has a hit in the event.  If it does, then
				// only add the hit to the event if it is "close" to the previous hit (part of
				// a cluster).  If it is the first hit for the module, add the hit to the event.

				/* 
				cout << " bco, bcolast = " << bco << ", " << bcolast << endl;
				cout << " foundhit= " << foundhit << endl;
				cout << " module, mchip, chan_id = " << module << ", " << mchip << ", " << chan_id << endl;
				cout << " nhitsmod = " << nhitsevent[module][mchip-1]<< endl;
				if (nhitsevent[module][mchip-1] > 0) {
				cout << " chanhits = " << chanhits[module][mchip-1][nhitsevent[module][mchip-1]-1] << endl;
				}
				*/ 

				if ( (firstevent || (bco >=  bcolast - 1 && bco <= bcolast + 1) ) &&  !foundhit){
//				if ( (firstevent || (bco >=  bcolast - 1 && bco <= bcolast + 1) ) && 
//					( !foundhit && (nhitsevent[module][mchip-1] == 0 ||  
//					(nhitsevent[module][mchip-1] > 0 && 
//                                        (chan_id <= chanhits[module][mchip-1][nhitsevent[module][mchip-1]-1] + 3 && 
//					chan_id >= chanhits[module][mchip-1][nhitsevent[module][mchip-1]-1] - 3) )) ) ){

						//cout << "Hit added to event" << endl;
						if (firstevent) firstevent = false;

						bcolast = bco;
						ichiplast[module] = chip_id;
						chanhits[module][mchip-1][nhitsevent[module][mchip-1]] = chan_id;
						adchits[module][mchip-1][nhitsevent[module][mchip-1]] = adc;
						nhitsevent[module][mchip-1]++;
				}
				else{
					//cout << "New event started " << endl;
					if (firstevent) firstevent = false;
					float ntvar[100]= {0};
					ntvar[0] = hitevent;
                
                                        // Find clusters in this event:
                                        int nclus[4][8] = {0};
	                                int cluswid[4][8][128] = {0};    // cluster width of each cluster found in a module, chip
	                                int chan1[4][8][128] = {0};      // first channel of each cluster found in a module, chip
                                        float chargeclus = 0;

                                        // Order hits in event and then look for clusters:
                                        int local_chan[128];
					for (int imodule = 0; imodule < 4; imodule++) {
					  for (int ichip = 0; ichip < 8; ichip++) {
					    for (int ihit = 0; ihit < nhitsevent[imodule][ichip]; ihit++) {
                                              local_chan[ihit] = chanhits[imodule][ichip][ihit];
                                            }
                                            sort(local_chan, local_chan + nhitsevent[imodule][ichip]);
                                            int chanlast = 999;

					    for (int ihit = 0; ihit < nhitsevent[imodule][ichip]; ihit++) {
                                              if (adchits[imodule][ichip][ihit] < 7)chargeclus = (adcconv[adchits[imodule][ichip][ihit]] + 
                                                 adcconv[adchits[imodule][ichip][ihit]+1])/2.0;
                                              else chargeclus = adcconv[adchits[imodule][ichip][ihit]];

                                              // See if this hit should be added to the cluster
                                              if (local_chan[ihit] == chanlast + 1){
                                                cluswid[imodule][ichip][nclus[imodule][ichip] - 1]++;
                                                adctot[imodule][ichip][nclus[imodule][ichip] - 1] += adchits[imodule][ichip][ihit];
                                                chargetot[imodule][ichip][nclus[imodule][ichip] - 1] += chargeclus;
                                                chargehit[imodule][ichip][nclus[imodule][ichip] - 1][cluswid[imodule][ichip][nclus[imodule][ichip] - 1] - 1] = chargeclus;
                                                cluspos[imodule][ichip][nclus[imodule][ichip] - 1] += chargeclus*local_chan[ihit];
                                              }
                                              // else create a new cluster
                                              else {
                                                chan1[imodule][ichip][nclus[imodule][ichip]] = local_chan[ihit];
                                                cluswid[imodule][ichip][nclus[imodule][ichip]]++;
                                                adctot[imodule][ichip][nclus[imodule][ichip]] = adchits[imodule][ichip][ihit];
                                                chargetot[imodule][ichip][nclus[imodule][ichip]] = chargeclus;
                                                chargehit[imodule][ichip][nclus[imodule][ichip]][0] = chargeclus;
                                                cluspos[imodule][ichip][nclus[imodule][ichip]] = chargeclus*local_chan[ihit];
                                                nclus[imodule][ichip]++;
                                              }
                                              chanlast = local_chan[ihit];
                                            }
                                          }
                                        }
                                           
                                        // Fill event ntuples before clearing out event variables:
                                        float pos;
                                        int nmodules[4] = {0};
					for (int imodule = 0; imodule < 4; imodule++) {
					  for (int ichip = 0; ichip < 8; ichip++) {
					    ntvar[1] += (float)nhitsevent[imodule][ichip];
                                            if (nclus[imodule][ichip]>0) nmodules[imodule] = 1;
					    for (int iclus = 0; iclus < nclus[imodule][ichip]; iclus++){

					      chipside = (ichip<4) ? ichip+1 : ichip - 3;
					      side = (ichip < 4) ? 0 : 1;
                                              // Calculate center-of-gravity position of cluster:
                                              pos = cluspos[imodule][ichip][iclus]/chargetot[imodule][ichip][iclus];

					      cluster->Fill(hitevent, imodule, side, chipside, chan1[imodule][ichip][iclus], 
                                                cluswid[imodule][ichip][iclus], adctot[imodule][ichip][iclus], bco, 
                                                nclus[imodule][ichip], chargetot[imodule][ichip][iclus], 
                                                pos, chargehit[imodule][ichip][iclus][0], chargehit[imodule][ichip][iclus][1],
                                                chargehit[imodule][ichip][iclus][2], chargehit[imodule][ichip][iclus][3]);

					      //Fill event ntuple variables:
					      ntvar[2]++;
					      ntvar[3+imodule] = (float)cluswid[imodule][ichip][iclus];
					      ntvar[7+imodule] = (float)adctot[imodule][ichip][iclus];
					      ntvar[11+imodule*3] = (float)imodule;
                                              chipside = (ichip<4) ? ichip  : ichip - 4;
                                              side = (ichip < 4) ? 0 : 1;
          
					      ntvar[12+imodule*3] = (float)chipside;
					      ntvar[13+imodule*3] = (float)chanhits[imodule][ichip][0];
					      ntvar[23+imodule] = (float)side;
					      ntvar[27+imodule] = chargetot[imodule][ichip][0];
                                              // Calculate the cluster position within the module:
					      ntvar[35+imodule] = (3 - chipside)*128 + (side*128 +
                                                (0.5 - side)*2*cluspos[imodule][ichip][0]/chargetot[imodule][ichip][0]);
                                              // Calculate the cluster position within the module without using charge:
					      ntvar[40+imodule] = (3 - chipside)*128 + (side*128 +
                                                (0.5 - side)*2*(chanhits[imodule][ichip][0] + cluswid[imodule][ichip][0]/2.0));

					    }
                                            ntvar[31 + imodule] += nclus[imodule][ichip];
					  }
					}

                                        for (int imodule=0; imodule<4; imodule++)if (nmodules[imodule]>0) ntvar[39]++;
					event->Fill(ntvar);

                                        // Zero out event arrays
					for (int imodule=0; imodule < 4; imodule++){
						ichiplast[imodule] = 999;
						for (int ichip=0; ichip < 8; ichip++){
							nhitsevent[imodule][ichip] = 0;
							for (int ihit=0; ihit < 128; ihit++){
							  chanhits[imodule][ichip][ihit] = 999;
							  usedhit[imodule][ichip][ihit] = 0;
							  cluswid[imodule][ichip][ihit] = 0;
							  adctot[imodule][ichip][ihit] = 0;
							  chargetot[imodule][ichip][ihit] = 0.0;
							}
						}
					}
                  
                                        // Initialize event variables for new event:
					hitevent++;
					bcolast = bco;
					ichiplast[module] = chip_id;
					chanhits[module][mchip-1][0] = chan_id;
					adchits[module][mchip-1][0] = adc;
					nhitsevent[module][mchip-1]++;
				}
                                chipside = (mchip<5) ? mchip - 1 : mchip - 5;
                                side = (mchip < 5) ? 0 : 1;
				hits->Fill(chan_id, ampl, adc, bco, chip_id, hitevent, fpga_id, module, chipside, side, charge, ievent);
				ievent++;

				//       cout << "chanid = " << chan_id << ", ampl = " << ampl << ", adc = " << adc << ", bco = " << bco <<
				//	      ",nhits = " << nhits[chan_id][ampl] << endl;

			}
			//			index = start + cnt - 2;
#ifdef OLD
			index = start + cnt + 2;
#else
			index = start + cnt;
#endif

		}  // If block on record type
	}  // Loop over events

	TCanvas *c1 = new TCanvas("c1","test",0,0,1000,800);
	c1->Divide(3,2);
	c1->Draw();

	// BCO distribution, ADC distribution, hit distribution, number of clusters found/event, cluster position versus. module #/side
	// Hit position versus module position (tracks)

	c1->cd(1);
	TH1F *h1 = new TH1F("h1","BCO Distribution;BCO;Counts", 64,-0.5, 63.5);
	gStyle->SetPalette(1);
	gPad->SetLogy();
	hits->Draw("bco>>h1","");

	c1->cd(2);
	TH1F *h2 = new TH1F("h2", "ADC Distribution;ADC Distribution for all Hits;Counts", 8, -0.5, 7.5);
	gPad->SetLogy();
	hits->Draw("adc>>h2");

	c1->cd(3);
	gPad->SetLogy();
	TH1F *h3 = new TH1F("h3", "Hit Distribution;Channel Number (module*1024+chip*128+chan);Counts", 4096, -0.5, 4095.5);
	hits->Draw("module*128*8+side*4*128+(chip)*128+chan_id>>h3");

	c1->cd(5);
	gPad->SetLogy();
	TH1F *h4 = new TH1F("h4", "Cluster Size Distribution;Cluster Size;Counts", 20, -0.5, 19.5);
	cluster->Draw("cluswid>>h4");

	c1->cd(6);
	gPad->SetLogy();
	//TH1F *h6=new TH1F("h6","ClusterCharge;Cluster Charge (ADC counts) ;Counts", 20, -0.5, 19.5);
	//cluster->Draw("adctot >> h6");
	TH1F *h6=new TH1F("h6","Number of Clusters;Number of Clusters;Counts", 40, -0.5, 39.5);
	event->Draw("nclus >> h6");

	int itest = 0;
	ievent = 0;
	char* str = new char[100];
	TH2F *h5 = new TH2F("h5", "Hit Position vs. Module;Module + Side;Cluster Position", 200, -0.5, 3.5, 512, -0.5, 511.5);        	
	h5->SetMarkerStyle(29);
	h5->SetMarkerColor(2);

	std::cout << "loop over entries, plotting event" << std::endl;
	gPad-> SetGridx();
	while (itest > -1 && ievent < event->GetEntries() ){	      
		c1->cd(4);
		gPad->SetGridx();
		gPad->SetGridy();

		// Channel id numbering is reversed from side to side.  One of these will correct this:


		float *vars = event->GetArgs();
		event->GetEntry(ievent);
                int nmod = 0;
		if (itest == 0) {
                        for (int imodule = 0; imodule < 4; imodule++) if (vars[31+imodule] > 0) nmod++;
			while (nmod < 3){
				ievent++;
				if ( ievent >= event->GetEntries() ) break; 
				event->GetEntry(ievent);
                                nmod = 0;
                                for (int imodule = 0; imodule < 4; imodule++) if (vars[31+imodule] > 0) nmod++;
			}
		}

		if (itest == 0){sprintf(str, "event == %i", ievent); }
		else { sprintf(str, "event == %i", itest); }

		cout << "event = " << vars[0] << ", nclus = " << vars[2] << ", nmodules = " << nmod << endl;

		//cluster->Draw("(chip - 1)*128 + side*128 + (0.5 - side)*2*chan1:module + side*0.1>>h5",str);
		cluster->Draw("(4 - chip)*128 + (side*128 + (0.5 - side)*2*chan1) :module + side*0.1>>h5",str);

		//cluster->Draw("(chip - 1)*128 + (1-side)*128 + (side-0.5)*2*chan1:module + side*0.1>>h5",str);
		//cluster->Draw("(4 - chip)*128 + (1-side)*128 + (side-0.5)*2*chan1:module + side*0.1>>h5",str);


		gPad->Modified();
		c1->cd(0);
		c1->Update();
		cout <<"\n Input 0 to continue, # to select a particular event, -1 to end display" << endl;
		cin >> itest;

		ievent++;
	}
	return;
}

int
getFileSize(std::ifstream& f)
{
	f.seekg(0,std::ifstream::end);
	if ( f.fail() )
	{
		std::ifstream::iostate state = f.rdstate();
		std::cout << "error seeking to end, read state = " << state << std::endl;
		if ( state & std::ios::eofbit )
			std::cout << " eof bit set" << std::endl;
		if ( state & std::ios::failbit )
			std::cout << " fail bit set" << std::endl;
		if ( state & std::ios::badbit )
			std::cout << " bad bit set" << std::endl;
		return 0;
	}
	int size = f.tellg();
	if ( size < 0 )
	{
		std::ifstream::iostate state = f.rdstate();
		std::cout << "error in tellg, read state = " << state << std::endl;
		if ( state & std::ios::eofbit )
			std::cout << " eof bit set" << std::endl;
		if ( state & std::ios::failbit )
			std::cout << " fail bit set" << std::endl;
		if ( state & std::ios::badbit )
			std::cout << " bad bit set" << std::endl;
		return 0;
	}

	// Return the file stream to the start of the file
	f.seekg(0,std::ifstream::beg);

	return size;
}

