#include <cstdio>

//void plot_calib(char* f_name = "C:/FVTX/data_0", int n_meas = 64, float maxscale = 200.)
void plot_calib_13chips(char* f_name = "C:/FVTX/data_0", int n_meas = 64, float maxscale = 200.)
{
	gStyle->SetOptFit(1);
	gStyle->SetOptStat(0);
	char cf_name[100];
	unsigned long int dataIn[1000000];
	long lSize;
	size_t result;

	int bco, adc, ampl, col_raw, col;
	int chan_id, n_hits, chip_id;

	FILE* cal_file;

	int NCHAN = 128;
	int NCHIPS = 26;

	TNtuple *hits = new TNtuple("hits","test","chan_id:ampl:adc:bco:chip_id:event");

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
	int nhits[26][128][1024];

	for (int ichan=0; ichan<NCHAN; ichan++)
		for (int iamp = 0; iamp < n_meas; iamp ++) 
                  for (int ichip = 0; ichip < NCHIPS; ichip ++) nhits[ichip][chan_id][iamp] = 0;

	// Extract bco, channel, amplitude, and adc from each hit, and count the number of 
	// hits at each amplitude for each channel:

    TH2F* h1[26];
    char* histname = new char[10];
    for (int ichip=0; ichip< NCHIPS; ichip++){
	      sprintf(histname,"h1_%i",ichip);
          h1[ichip] = new TH2F(histname, "Amplitude vs Chan;Channel ID;Amplitude[DAC units]",128,-0.5,127.5,64,-0.5,63.5);
  	      h1[ichip]->SetMaximum(maxscale);
    }

    int found[13] = {0};
    int chipnotfound[13] = {0};
    int countchips = 0;
    int ievent = 0;
//	while (ievent < 1000)
	while(1)
	{
		result = fread (dataIn, sizeof(unsigned long int), 1000000, cal_file);
		ievent = 0;
		while (ievent < result )
		{

			bco = (dataIn[ievent]&0x1f800000)>>23;
			chan_id = (dataIn[ievent]&0xfe00)>>9;
			adc = (dataIn[ievent]&0xe0000000)>>29;
			ampl = (dataIn[ievent]&0x7e0000)>>17;
			chip_id = (dataIn[ievent]&0xfc)>>2;
    
			nhits[chip_id-1][chan_id][ampl]++;

/*
			if (countchips < 13){
                found[chip_id-1] = 1;
                countchips++;
            }               
            else{
                for (int ichip=0; ichip<13; ichip++){
                    if (found[ichip] == 0){
                        cout << "ichip = " << ichip << " not found in event = " << ievent << endl;
                        chipnotfound[ichip]++;
                    }
                }
                for (int ichip=0; ichip<13; ichip++)found[ichip] = 0;
                countchips = 0;
            } 
*/
			if (ievent == 10) cout<<hex<<dataIn[ievent]<<" "<<chan_id<<" "<<bco<<" "<<ampl<<" "<<chip_id<<endl;
			
			hits->Fill(chan_id, ampl, adc, bco, chip_id, ievent);
	        if (bco==40 ||bco==41) h1[(int)(chip_id-1)]->Fill(chan_id,ampl);
			//       cout << "chanid = " << chan_id << ", ampl = " << ampl << ", adc = " << adc << ", bco = " << bco <<
			//	      ",nhits = " << nhits[chan_id][ampl] << endl;
			ievent++;
		}
		if (result != 1000000) break;
	}
	fclose(cal_file);

/*
    for (int ichip=0; ichip<13; ichip++){
           cout << "Missing hits from chip = " << ichip << " = " << chipnotfound[ichip] << endl;
    }
*/

	TCanvas *c1 = new TCanvas("c1","Amplitude vs. Channel",50,50,1200,800);
	c1->Divide(7,2);
	c1->Draw();

	gStyle->SetPalette(1);

	c1->cd(1);
        h1[0]->Draw("color4z");
  	c1->cd(2);
        h1[1]->Draw("color4z");
  	c1->cd(3);
        h1[2]->Draw("color4z");
  	c1->cd(4);
        h1[3]->Draw("color4z");
  	c1->cd(5);
        h1[4]->Draw("color4z");
  	c1->cd(6);
        h1[5]->Draw("color4z");
  	c1->cd(7);
        h1[6]->Draw("color4z");
  	c1->cd(8);
        h1[7]->Draw("color4z");
  	c1->cd(9);
        h1[8]->Draw("color4z");
  	c1->cd(10);
        h1[9]->Draw("color4z");
  	c1->cd(11);
        h1[10]->Draw("color4z");
  	c1->cd(12);
        h1[11]->Draw("color4z");
  	c1->cd(13);
        h1[12]->Draw("color4z");

/*
	TCanvas *c2 = new TCanvas("c2","ADC vs. Pulser Amplitude",70,70,1220,820);
	c2->Divide(7,2);
	c2->Draw();
        c2->cd(1);
	c2->GetPad(2)->SetGrid(1,1);
        TH2F *h2_0=new TH2F("h2_0","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_0","(chip_id == 1)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
	c2->cd(2);
        TH2F *h2_1=new TH2F("h2_1","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_1","(chip_id == 2)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
	c2->cd(3);
        TH2F *h2_2=new TH2F("h2_2","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_2","(chip_id == 3)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
	c2->cd(4);
        TH2F *h2_3=new TH2F("h2_3","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_3","(chip_id == 4)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
	c2->cd(5);
        TH2F *h2_4=new TH2F("h2_4","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_4","(chip_id == 5)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
	c2->cd(6);
        TH2F *h2_5=new TH2F("h2_5","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_5","(chip_id == 6)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
	c2->cd(7);
        TH2F *h2_6=new TH2F("h2_6","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_6","(chip_id == 7)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
	c2->cd(8);
        TH2F *h2_7=new TH2F("h2_7","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_7","(chip_id == 8)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
	c2->cd(9);
        TH2F *h2_8=new TH2F("h2_8","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_8","(chip_id == 9)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
	c2->cd(10);
        TH2F *h2_9=new TH2F("h2_9","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_9","(chip_id == 10)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
	c2->cd(11);
        TH2F *h2_10=new TH2F("h2_10","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_10","(chip_id == 11)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
	c2->cd(12);
        TH2F *h2_11=new TH2F("h2_11","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_11","(chip_id == 12)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
	c2->cd(13);
        TH2F *h2_12=new TH2F("h2_12","ADC vs Amplitude;Amplitude[DAC units];ADC",64,-0.5,63.5,8,-0.5,7.5);
	hits->Draw("adc:ampl>>h2_12","(chip_id == 13)&&!(chan_id==98||(chan_id>-1&&chan_id<15)||chan_id==124||chan_id==126)","box");
*/
}
