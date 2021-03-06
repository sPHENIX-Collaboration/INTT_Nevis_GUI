Double_t erf( Double_t *x, Double_t *par){   //<===========
  return 50.*TMath::Erfc((-x[0]+par[0])/par[1]); //<===========
}

#include <cstdio>

//
//dac_e_conv nominal value comes from:
//    * DAC output = 0-2.67V full scale for 10 bits (1023). With 20 dB attenuator, full scale - 0 - 0.267V = 0.261 mV/DAC bit
//    * The calibration code (you should double-check on your particular test stand) is sending out pulser amplitudes from 0 - 252 (0011111100) in 4-bit steps.
//    * Thus the voltage/calibration step = 1.044 mV/amplitude bit
//    * The injection capacitors are nominally 25 fF.
//    * Electrons/pulser amplitude bit = (1.044*10-3 mV)*(25*10-15 F)/(1.6*10-19 C/e) = 163.1 electrons/DAC bit.
//    * For the Xilinx test stand board, the pulser output is 0-2.0 V, so the conversion factor should be 122.1 if the same attenuator, etc. are used. 
// Some emperical tuning may be needed for the first factor as it was found that for a LANL test stand the full voltage range was different
// from the nominal 0-2.67V and 163.1 went to 99.1
//
void Noise_26ChipModule_June10(char* fname = "C:/FVTX/data_0", int n_meas = 64, float dac_e_conv = 99.1, int mode =0, int t_chan = 17, float gainfitmin = 20.0 , float gainfitmax = 40.0, int t_chip = 1)
{
   gStyle->SetOptFit(1);
   gStyle->SetOptStat(0);
   char cf_name[100],of_name[100],tmp[100];
   double v0, dv;
   TH1F *hh[32][128];    // Histogram to hold number of hits versus amp for each channel
   int mean_exp[32][128],dead_chan[30000],n_dead=0,vref,vth0,n_steps;
   TLatex txt;
   unsigned long int dataIn[1000000];
   long lSize;
   size_t result;
   int bco, adc, ampl, col_raw, col, fpga_id, mchip;

   int chan_id, n_hits, chip_id;

   n_steps = 100;
   v0 = 3;
   dv =1;

   cout << dv << endl;
   TF1 *fit = new TF1("fit", (void *)erf, v0, v0+dv*n_meas, 2);

   int NCHAN = 128;
   int NCHIPS = 26;
   
   ofstream out_file;   
   sprintf( of_name, "%s.fit", fname );
   out_file.open( of_name );

   // Create histograms for each channel in each chip:
   for (int ichan = 0; ichan < NCHAN ; ichan++)
   {
     for (int ichip = 0; ichip < NCHIPS ; ichip++)
     {
       sprintf( tmp, "hist_%i_%i", ichip, ichan );
//     hh[ichan] = new TH1F( tmp, tmp, n_meas, v0-0.5*dv, v0+(n_meas-0.5)*dv);
       hh[ichip][ichan] = new TH1F( tmp, ";Amplitude (DAC units); Counts", 250, v0-0.5*dv, v0+(250-0.5)*dv);
       hh[ichip][ichan]->SetMarkerColor(2);
       hh[ichip][ichan]->SetMarkerStyle(8);
       hh[ichip][ichan]->SetMarkerSize(1);
       hh[ichip][ichan]->SetMinimum(-5);
//       hh[ichip][ichan]->SetMaximum(n_steps*1.1);
       mean_exp[ichip][ichan] = 0;
       sprintf( tmp, "gain_%i_%i", ichip, ichan );
     }
   }


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
   int nhits[32][128][1024];

   for (int ichan=0; ichan<NCHAN; ichan++)
     for (int iamp = 0; iamp < n_meas; iamp ++) 
       for (int ichip = 0; ichip < NCHIPS; ichip ++) nhits[ichip][ichan][iamp] = 0;

   // Extract bco, channel, amplitude, and adc from each hit, and count the number of 
   // hits at each amplitude for each channel:

    int ievent = 0;
    int bufcnt = 0;

    for (int index=0; index<size/sizeof(unsigned int); bufcnt++)
    {
      // Get record size
      int start = index;
      int cnt = data[start];

      // Unpack the record
      int word0 = data[start];
      int word1 = data[start+1];
      int word2 = data[start+2];
      if ( word1 == 0xFFFFFFFF && word2 == 0xFFFFFFFF )
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
	    index = start + cnt + 2;
	    continue;
	  }
      else if ( word0 == 4 )
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
	    unsigned char* p2 = &p[n];
	    for(int n=0; n<16; n++)
	    {
	      std::cout << "      Reg " << n << ": " << (int) p2[n] << std::endl;
	    }
	    index = start + cnt + 2; 
	  }
      else
	  {
	    // Format of record is 
	    //   data[0] = # of data words
	    //   data[1..n] = data words
	    //   data[n+1] = checksum for buffer
	    //std::cout << "Buffer " << bufcnt << ": Data record, "
		//    << "nwords = " << cnt << " checksum = " 
		//    << "0x" << std::hex << std::setw(8) << set::setfill('0') << data[index+cnt+1] << std::dec << std::endl;
	    int checksum = 0;
	    for ( index++; index<start+cnt+1; index++)
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
		  fpga_id = (data[index]&0x80)>>7;
		  ampl = (data[index]&0x7e0000)>>17;

		  if (fpga_id == 0) {
		    module = 0;
		  }
		  else{
		    module = 1;
		  }
		  mchip = chip_id;

		  //Decoding for FPHX-2:
		  // DDXB BBBB BAAA AAA1 CCCC CCBC FIII  IID0
		    // D = ADC, B = BCO, A = AMPLITUDE, C = CHAN_ID, F = FPGA_ID, I = CHIP_ID
		  bco = ((data[index] & 0x200) >> 3) | ((data[index] & 0x1f800000) >> 23);
		  chan_id = ((data[index] & 0x100) >> 2) | ((data[index] & 0xfc00) >> 10);
		  adc = (data[index] & 0x2 << 1) | ((data[index] & 0xc0000000) >> 30);

		  if (bco == 0 && chip_id>0 && chip_id < 14) nhits[module*13+mchip-1][chan_id][ampl]++;

		  if (ievent < 10) cout<< "Raw data = " << hex << data[index]
		                   <<", chip_id =  " << chip_id << ", chan_id =  " <<c han_id
						   <<", bco = " << bco << ", ampl = " << ampl
						   <<", fpga = " << fpga_id << endl;

          ievent++;
     }

	 index++;

   }  // If block on record type

  }  // Loop over events


   // Fill histogram with the number hits at each amplitude, and the mean_exp with the amplitude at
   // which there are n_steps/2 hits:

   for (int ichip = 0; ichip < NCHIPS; ichip ++){
     for (int ichan=0; ichan<NCHAN; ichan++){
       for (int iamp = 0; iamp < n_meas; iamp ++){

	   //if (ichip == 1 && ichan == 25) cout << "nhits = " << nhits[ichip][ichan][iamp]<<endl;

	   if (mean_exp[ichip][ichan]==0 && nhits[ichip][ichan][iamp] > (n_steps/2)) {
             mean_exp[ichip][ichan] = iamp;
             //cout << "ichip = " << ichip << ", ichan = " << ichan << ", mean = " << mean_exp[ichip][ichan] << endl;
       }

	   hh[ichip][ichan]->SetBinContent(iamp+1, nhits[ichip][ichan][iamp]);

	   if (nhits[ichip][ichan][iamp] != 0 && nhits[ichip][ichan][iamp] < n_steps)
  	     hh[ichip][ichan]->SetBinError(iamp + 1, 
                sqrt((float)nhits[ichip][ichan][iamp]*(1.-((float)nhits[ichip][ichan][iamp]/(float)n_steps))));
	   else 
	     hh[ichip][ichan]->SetBinError(iamp+1,1.0);

       }
     }
   }

   // Create output file with histograms:

   sprintf( of_name, "%s.fit", fname );
   out_file.open( of_name );

   TH1F *mean = new TH1F( "mean", "Mean distribution;Threshold [e]", 200, 0, 15000);
   TH1F *mean1 = new TH1F( "mean", "Mean distribution (FPHX-1);Threshold [e]", 200, 0, 7000);
   TH1F *mean2 = new TH1F( "mean", "Mean distribution (FPHX-2);Threshold [e]", 200, 0, 7000);
   TH1F *rms = new TH1F( "rms", "RMS distribution;Noise [e]", 200, 0., 1200);
   TH2F *mean2d = new TH2F("mean2d","Mean distribution;Channel",4096,-0.5,4095.5,100,-0.5,15000.);
   TH2F *rms2d = new TH2F("rms2d","RMS distribution;Channel",4096,-0.5,4095.5,100,-0.5,1200.);

//   mean2d->SetMinimum(20);
//   mean2d->SetMaximum(70);
//   rms2d->SetMinimum(1.5);
//   rms2d->SetMaximum(6);

   mean->GetXaxis()->SetLabelSize(0.03);
   mean1->GetXaxis()->SetLabelSize(0.03);
   mean2->GetXaxis()->SetLabelSize(0.03);
   rms->GetXaxis()->SetLabelSize(0.03);
   mean->GetYaxis()->SetLabelSize(0.03);
   mean1->GetYaxis()->SetLabelSize(0.03);
   mean2->GetYaxis()->SetLabelSize(0.03);
   rms->GetYaxis()->SetLabelSize(0.03);
   mean2d->GetXaxis()->SetLabelSize(0.03);
   rms2d->GetXaxis()->SetLabelSize(0.03);
   mean2d->GetYaxis()->SetLabelSize(0.03);
   rms2d->GetYaxis()->SetLabelSize(0.03);
   mean2d->GetZaxis()->SetLabelSize(0.03);
   rms2d->GetZaxis()->SetLabelSize(0.03);
   mean2d->SetMarkerStyle(2);
   mean2d->SetMarkerColor(2);
   rms2d->SetMarkerStyle(2);
   rms2d->SetMarkerColor(2);


   if (mode) {
     printf("nhits[t_chip][t_chan][30] = %i\n", n_steps);
	 printf("mean_exp = %f\n",mean_exp[t_chip][t_chan]);
	 float fmin = v0+(mean_exp[t_chip][t_chan]-40.)*dv;
	 float fmax = v0+(mean_exp[t_chip][t_chan]+40.)*dv;
     cout << "fmin, fmax = " << fmin << ", " << fmax << endl;
     gStyle->SetOptStat(0);
     gStyle->SetOptFit(0);
     gStyle->SetOptTitle(0);
     hh[t_chip][t_chan]->Draw();
     fit->SetParameter(0, v0 + mean_exp[t_chip][t_chan]*dv );
     cout << v0 + mean_exp[t_chip][t_chan]*dv << endl;
     fit->SetParameter(1, 6.*dv);         
//     hh[t_chan]->Fit("fit","RQ","same",v0+(mean_exp[t_chan]-20.)*dv,v0+(mean_exp[t_chan]+20.)*dv);
     hh[t_chip][t_chan]->Fit("fit","RQ","same",v0+(mean_exp[t_chip][t_chan]-40.)*dv,v0+(mean_exp[t_chip][t_chan]+40.)*dv);
     break;
   }
	
   for (int ichan = 0; ichan < NCHAN; ichan++) {
     for (int ichip = 0; ichip < NCHIPS; ichip++) {

       if (mean_exp[ichip][ichan] >0) {
         fit->SetParameter( 0, v0 + mean_exp[ichip][ichan]*dv );
         fit->SetParameter( 1, 1.4*dv );
         if (mean_exp[ichip][ichan]!=0) {
           hh[ichip][ichan]->Fit("fit","RQMN","",v0+(mean_exp[ichip][ichan]-20.)*dv,v0+(mean_exp[ichip][ichan]+20.)*dv);
//         cout << "ichan " << ichan << " mean fit = " << fit->GetParameter(0)*dac_e_conv << endl;
//         cout << "ichan " << ichan << " rms fit = " << fit->GetParameter(1)*dac_e_conv << endl;
           mean->Fill(fit->GetParameter(0)*dac_e_conv);
           if (ichip > 7 && ichip < 11) mean1->Fill(fit->GetParameter(0)*dac_e_conv);
           else if (ichip > 24) mean2->Fill(fit->GetParameter(0)*dac_e_conv);

           rms->Fill(fit->GetParameter(1)*dac_e_conv);
		   
           mean2d->Fill(ichip*NCHAN + ichan, fit->GetParameter(0)*dac_e_conv);
           rms2d->Fill(ichip*NCHAN + ichan, fit->GetParameter(1)*dac_e_conv);
         }
         else {
         }

         out_file<<ichan<<" "<<fit->GetParameter(0)<<" "<<fit->GetParError(0)<<" "<<fit->GetParameter(1)<<" "<<fit->GetParError(1)<<endl;
       }
       else { 
         out_file<<ichan<<" 50% level was not crossed (dead channel)"<<endl;
         dead_chan[n_dead]= ichan;
         n_dead ++;
       }
     }
   }

   out_file.close();
 

   TCanvas *c1 = new TCanvas("c1","Mean & RMS distribution",50,0,1200,900);
   c1->Divide(2,2);
//   c1_1->SetPad(0.0,0.5,0.4,1.0);
//   c1_2->SetPad(0.4,0.5,0.8,1.0);
//   c1_3->SetPad(0.0,0.0,0.4,0.5);
//   c1_4->SetPad(0.4,0.0,0.8,0.5);
   c1_1->cd();
     mean->SetLineColor(2);
     mean->SetLineWidth(2);
     mean->Draw();
     mean->Fit("gaus","Q same");
     //mean1->SetLineColor(2);
     //mean1->SetLineWidth(2);
     //mean1->Draw();
     //mean1->Fit("gaus","Q same");
   c1_2->cd();
     rms->SetLineColor(4);
     rms->SetLineWidth(2);
     rms->Draw();
     rms->Fit("gaus","Q same","", 100, 1000);
     //mean2->SetLineColor(2);
     //mean2->SetLineWidth(2);
     //mean2->Draw();
     //mean2->Fit("gaus","Q same");
     //gStyle->SetOptStat(0);
	c1_3->cd();
	 c1_3->SetGridx();
	 mean2d->GetXaxis()->SetNdivisions(8,0);
	 mean2d->Draw("color4z");
	//     mean2d->Draw("");
	 gStyle->SetPalette(1);
	c1_4->cd();
	 c1_4->SetGridx();
	 rms2d->GetXaxis()->SetNdivisions(8,0);
	 rms2d->Draw("color4z");
     gStyle->SetPalette(1);
   //c1->cd();
   //  txt.SetTextSize(0.02);
   //  txt.DrawLatex(0.82,0.95,"Input file:");
   //  txt.DrawLatex(0.82,0.90,cf_name);
   //  sprintf(tmp,"V_{REF} = %i",vref);
   //  txt.DrawLatex(0.82,0.82,tmp);
   //  sprintf(tmp,"V_{TH0} = %i",vth0);
   //  txt.DrawLatex(0.82,0.77,tmp);
   //  sprintf(tmp,"N_{STEP} = %i",n_steps);
   //  txt.DrawLatex(0.82,0.72,tmp);
   //  sprintf(tmp,"N_{MEAS} = %i",n_meas);
   //  txt.DrawLatex(0.82,0.67,tmp);
   //  sprintf(tmp,"Thr = %d #pm %d [e]",mean->GetFunction("gaus")->GetParameter(1),mean->GetFunction("gaus")->GetParameter(2));
   //  txt.DrawLatex(0.80,0.60,tmp);
   //  sprintf(tmp,"Noise = %d #pm %d [e]",rms->GetFunction("gaus")->GetParameter(1),rms->GetFunction("gaus")->GetParameter(2));
   //  txt.DrawLatex(0.80,0.56,tmp);
   //  sprintf(tmp,"%i dead pixel:",n_dead);
   //  txt.DrawLatex(0.80,0.48,tmp);

   //for (int i=0;i<n_dead ;i++ ) {
   //  sprintf(tmp,"[%i;%i]",dead_chan[i]);
   //  double x_pos  = 0.81+0.045*(i-(i/4)*4.);
   //  double y_pos = 0.44-(i/4)*0.02;
   //  txt.SetTextSize(0.02);
   //  txt.DrawLatex(x_pos,y_pos,tmp);
   //  if (i > 81) then {
   //    txt.DrawLatex(x_pos+0.05,y_pos,"...");
   //    break;
   //  }
   //}
   c1->cd();
   sprintf(tmp,"%s.pdf",fname);
   c1->Print(tmp);
   sprintf(tmp,"%s.gif",fname);
   c1->Print(tmp);
   c1->Update();
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
      return;
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
      return;
    }

  // Return the file stream to the start of the file
  f.seekg(0,std::ifstream::beg);

  return size;
}
