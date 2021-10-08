Double_t erf( Double_t *x, Double_t *par){   //<===========
  return 50.*TMath::Erfc((-x[0]+par[0])/par[1]); //<===========
}

#include <cstdio>

void Erf_fit_fphx_nhits_13chips(char* f_name = "C:/FVTX/data_0", int n_meas = 64, float dac_e_conv = 163.1, int mode =0, int t_chan = 17, float gainfitmin = 20.0 , float gainfitmax = 40.0, int t_chip = 1)
{
   gStyle->SetOptFit(1);
   gStyle->SetOptStat(0);
   char cf_name[100],of_name[100],tmp[100];
   double v0, dv;
   TH1F *hh[26][128];    // Histogram to hold number of hits versus amp for each channel
   int mean_exp[26][128],dead_chan[30000],n_dead=0,vref,vth0,n_steps;
   TLatex txt;
   unsigned long int dataIn[1000000];
   long lSize;
   size_t result;
   int bco, adc, ampl, col_raw, col;

   int chan_id, n_hits, chip_id;

   FILE* cal_file;
   ofstream out_file;

   n_steps = 100;
   v0 = 3;
   dv =1;

   cout << dv << endl;
   TF1 *fit = new TF1("fit", (void *)erf, v0, v0+dv*n_meas, 2);

   int NCHAN = 128;
   int NCHIPS = 13;

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
   // cout << "bytesize for each element = " << sizeof(unsigned long int) <<endl;
   // cout << "Size of cal file to read = " << lSize <<endl;

   // int nelements = lSize/sizeof(unsigned long int);

   // Do a block read of data from file and put into array dataIn:
   //result = fread (dataIn, sizeof(unsigned long int), nelements, cal_file);

   //if (result != nelements) {
   //	  cout << "Error reading input file, result = " << result << endl;
   //	  exit;
   // }


   // Counter to count the number of hits for each channel and amplitude:
   int nhits[26][128][1024];

   for (int ichan=0; ichan<NCHAN; ichan++)
     for (int iamp = 0; iamp < n_meas; iamp ++) 
       for (int ichip = 0; ichip < NCHIPS; ichip ++) nhits[ichip][ichan][iamp] = 0;

   // Extract bco, channel, amplitude, and adc from each hit, and count the number of 
   // hits at each amplitude for each channel:

   int ievent = 0;
   while (1)
   {
//   while (ievent < nelements )
     result = fread (dataIn, sizeof(unsigned long int), 1000000, cal_file);
     cout << "Reading " << result << " bytes of data." << endl;
     ievent = 0;
     while (ievent < result)
     {
           bco = (dataIn[ievent]&0x1f800000)>>23;
           chan_id = (dataIn[ievent]&0x00FE00)>>9;
           adc = (dataIn[ievent]&0xe0000000)>>29;
           ampl = (dataIn[ievent]&0x7E0000)>>17;
           chip_id = (dataIn[ievent]&0x00FC)>>2;

	       if (bco==41) nhits[chip_id-1][chan_id][ampl]++;

//        if (ievent < 10) 
//          cout << "chip_id = " << chip_id << ", chanid = " << chan_id << ", ampl = " << ampl << ", nhits = " << nhits[chip_id-1][chan_id][ampl] << endl;

           ievent++;
     }
     if (result != 1000000){
       cout << "Finished reading file " << endl;
       break;
     }
   }

   fclose(cal_file);

   // Fill histogram with the number hits at each amplitude, and the mean_exp with the amplitude at
   // which there are n_steps/2 hits:

   for (int ichip = 0; ichip < NCHIPS; ichip ++){
     for (int ichan=0; ichan<NCHAN; ichan++){
       for (int iamp = 0; iamp < n_meas; iamp ++){

	   if (mean_exp[ichip][ichan]==0 && nhits[ichip][ichan][iamp] > (n_steps/2)) {
             mean_exp[ichip][ichan] = iamp;
//             cout << "ichip = " << ichip << ", ichan = " << ichan << ", mean = " << mean_exp[ichip][ichan] << endl;
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

   sprintf( of_name, "%s.fit", f_name );
   out_file.open( of_name );

   TH1F *mean = new TH1F( "mean", "Mean distribution;Threshold [e]", 200, 0, 5000);
   TH1F *rms = new TH1F( "rms", "RMS distribution;Noise [e]", 200, 0., 1000);
   TH2F *mean2d = new TH2F("mean2d","Mean distribution;Channel",1664,-0.5,1663.5,30,-0.5,5000.);
   TH2F *rms2d = new TH2F("rms2d","RMS distribution;Channel",1664,-0.5,1663.5,30,-0.5,800.);

//   mean2d->SetMinimum(20);
//   mean2d->SetMaximum(70);
//   rms2d->SetMinimum(1.5);
//   rms2d->SetMaximum(6);

   mean->GetXaxis()->SetLabelSize(0.03);
   rms->GetXaxis()->SetLabelSize(0.03);
   mean->GetYaxis()->SetLabelSize(0.03);
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
 

   TCanvas *c1 = new TCanvas("c1","Mean & RMS distribution",50,0,800,800);
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
   c1_2->cd();
     rms->SetLineColor(4);
     rms->SetLineWidth(2);
     rms->Draw();
     rms->Fit("gaus","Q same","", 100, 1000);
     //gStyle->SetOptStat(0);
   c1_3->cd();
     mean2d->Draw("color4z");
//     mean2d->Draw("");
     gStyle->SetPalette(1);
   c1_4->cd();
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
   sprintf(tmp,"%s.pdf",f_name);
   c1->Print(tmp);
   sprintf(tmp,"%s.gif",f_name);
   c1->Print(tmp);
   c1->Update();
}
