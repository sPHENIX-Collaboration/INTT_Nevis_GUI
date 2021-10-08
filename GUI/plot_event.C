#include <cstdio>

void plot_event(char* f_name = "data_0", int n_meas = 64, float maxscale = 200.)
{
	gStyle->SetOptFit(1);
	gStyle->SetOptStat(0);
	char cf_name[100];
	unsigned long int dataIn[1000000];
	long lSize;
	size_t result;

	int bco, adc, ampl, col_raw, col, chip_id;
	int chan_id, n_hits;

	FILE* cal_file;

	int NCHAN = 128;

	TNtuple *hits = new TNtuple("hits","test","chan_id:ampl:adc:bco:chip_id:event");
	TNtuple *event = new TNtuple("event","test","event:nhits:cluswid:adctot:chip1:chan1");

	// Open the input calibration binary file:
	sprintf(cf_name,"%s.dat",f_name);
	cout<<" File name = "<< cf_name<<endl;
	cal_file = fopen(cf_name, "rb");

	if (!cal_file) {
		cout << "Calibration file not found " << endl;
		break;
	}


	// obtain file size:
	fseek (cal_file , 0 , SEEK_END);
	lSize = ftell (cal_file);
	rewind (cal_file);

	// Check our file reading parameters:
	cout << "bytesize for each element = " << sizeof(unsigned long int) <<endl;
	cout << "Size of cal file to read = " << lSize <<endl;

	int nelements = 1000000;//lSize/sizeof(unsigned long int);

	// Do a block read of data from file and put into array dataIn:

	//if (result != nelements) {
	//	cout << "Error reading input file, result = " << result << endl;
	//	exit;
	//}

	// Counter to count the number of hits for each channel and amplitude:
	int nhits[128][1024];

	for (int ichan=0; ichan<NCHAN; ichan++)
		for (int iamp = 0; iamp < n_meas; iamp ++) nhits[chan_id][iamp] = 0;

	// Extract bco, channel, amplitude, and adc from each hit, and count the number of 
	// hits at each amplitude for each channel:

	int ievent = 0;
	int hitevent = 0;
	//   while (ievent < 100)

        int bcolast = -999;
        int nhitsevent = 1;
        int cluswid = 0;
        int adctot = 0;
        int ichanlast = -999;
        int ichiplast = -999;

	while(1)
	{
		result = fread (dataIn, sizeof(unsigned long int), 1000000, cal_file);
		ievent = 0;
		hitevent = 0;
		while (ievent < result )
		{

			bco = (dataIn[ievent]&0x1f800000)>>23;
			chan_id = (dataIn[ievent]&0xfe00)>>9;
			chip_id = (dataIn[ievent]&0xfc)>>2;
			adc = (dataIn[ievent]&0xe0000000)>>29;
			ampl = (dataIn[ievent]&0x7e0000)>>17;
			nhits[chan_id][ampl]++;
			if (ievent == 10) cout<<hex<<dataIn[ievent]<<" "<<chan_id<<" "<<bco<<" "<<ampl<<endl;

			hits->Fill(chan_id,ampl,adc,bco,chip_id,ievent);

                        if (bco == bcolast){
                          nhitsevent++;
                          if ((chan_id == ichanlast+1 || chan_id == ichanlast-1) 
                                && (chip_id == ichiplast)) {
                            cluswid++;
                            adctot += (adc + 1);
                          }
                          else{
                            adctot = adc + 1;
                          }
                          bcolast = bco;
                          ichiplast = chip_id;
                          ichanlast = chan_id;
                        }
                        else{
                          event->Fill(hitevent, nhitsevent, cluswid, adctot, ichiplast, ichanlast);
                          hitevent++;
                          bcolast = bco;
                          ichiplast = chip_id;
                          ichanlast = chan_id;
                          nhitsevent = 1;
                          adctot = (adc + 1);
                          cluswid = 1;
                        }
			ievent++;

			//       cout << "chanid = " << chan_id << ", ampl = " << ampl << ", adc = " << adc << ", bco = " << bco <<
			//	      ",nhits = " << nhits[chan_id][ampl] << endl;
		}
		if (result != 1000000) break;
	}
	fclose(cal_file);

	TCanvas *c1 = new TCanvas("c1","test",100,50,650,800);
	c1->Divide(1,2);
	c1->Draw();

	c1->cd(1);
	c1->GetPad(1)->SetGrid(1,1);
	TH2F *h1 = new TH2F("h1","Amplitude vs Chan;Channel ID;Amplitude[DAC units]",128,-0.5,127.5,64,-0.5,63.5);
	h1->SetMaximum(maxscale);
	cout << endl;
	cout << "NOTE: Amplitude vs. Channel histogram has cut on BCO" << endl;
	cout << endl;
	gStyle->SetPalette(1);
	hits->Draw("ampl:chan_id>>h1","bco==41","color4z");

	c1->cd(2);
	c1->GetPad(2)->SetGrid(1,1);
	TH2F *h2=new TH2F("h2","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	//hits->Draw("adc:ampl>>h2","bco>16&&bco<18","box");
	TH1F *h3 = new TH1F("h3","BCO",64, -0.5, 63.5);
	//c1_2->SetLogy();
	gStyle->SetOptStat();
	//hits->Draw("bco>>h3","bco<40||bco>44");
        TH1F *ch1 = new TH1F("ch1","chan_id",128,-0.5,127.5);
	hits->Draw("chan_id>>ch1","bco<40||bco>44");

}
