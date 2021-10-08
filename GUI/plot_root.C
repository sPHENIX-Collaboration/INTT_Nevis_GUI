#include <TTree.h>
#include <TPad.h>
#include <TH1F.h>
#include <TH2F.h>
#include <iostream>
#include <TCut.h>
#include <TCanvas.h>
#include <TLegend.h>
#include <TLatex.h>

TCut load_chanmask(int);

void
plot_root(TTree* t, TTree* T1,
	  unsigned int hdi_type = 0, // 0==single chip, 1=kapton
	  int bco_min = 0,
	  int bco_max = 2,
	  int nevis_cut=1 // The single-chip boards have some channels bonded out
	  )
{
  if ( hdi_type > 1 ) 
    {
      std::cout << "Unknown HDI type: " << hdi_type << std::endl;
      return;
    }

  unsigned int runnumber;
  T1->SetBranchAddress("runnumber",&runnumber);
  T1->GetEntry(0);

  std::cout << "HDI type = " << hdi_type << std::endl;
  std::cout << "Processing run number " << runnumber << std::endl;

  int nchan = hdi_type == 0? 128 : 3328; //1664;
  int nbco = 64;
  int namp = 64;
  int nadc = 8;

  TH1* hChanRaw = new TH1F("hChanRaw","Raw Channel Dist;Channel;",nchan,-0.5,nchan-0.5);
  TH1* hBcoRaw = new TH1F("hBcoRaw","Raw BCO Dist;BCO;",nbco,-0.5,nbco-0.5);
  TH1* hBcoChanRaw = new TH2F("hBcoChanRaw","Raw BCO vs Chan Dist;Channel;BCO",nchan,-0.5,nchan-0.5,nbco,-0.5,nbco-0.5);

  TH1* hChanNoNoise = new TH1F("hChanNoNoise","Channel Dist, noisy channels cut;Channel;",nchan,-0.5,nchan-0.5);
  TH1* hBcoNoNoise = new TH1F("hBcoNoNoise","BCO Dist, noisy channels cut;BCO;",nbco,-0.5,nbco-0.5);
  TH1* hBcoChanNoNoise = new TH2F("hBcoChanNoNoise","BCO vs Chan Dist, noisy channels cut;Channel;BCO",nchan,-0.5,nchan-0.5,nbco,-0.5,nbco-0.5);
  
  TH1* hAmpRaw = new TH1F("hAmpRaw","Raw Amplitude Dist;Amplitude (DAC units);",namp,-0.5,namp-0.5);
  TH1* hAdcRaw = new TH1F("hAdcRaw","Raw ADC Dist;ADC;",nadc,-0.5,nadc-0.5);
  TH1* hAmpNoNoise = new TH1F("hAmpNoNoise","Amp Dist, noisy channels cut;Amplitude (DAC units);",namp,-0.5,namp-0.5);
  TH1* hAdcNoNoise = new TH1F("hAdcNoNoise","ADC Dist, noisy channels cut;ADC;",nadc,-0.5,nadc-0.5);
  TH1* hAmpChanRaw = new TH2F("hAmpChanRaw","Raw Amp vs Channel Dist;Channel;Amplitude (DAC units)",
			      nchan,-0.5,nchan-0.5,namp,-0.5,namp-0.5);
  TH1* hAmpChanNoNoise = new TH2F("hAmpChanNoNoise","Amp vs Chan Dist, noisy channels cut;Channel;Amplitude (DAC units)",
				  nchan,-0.5,nchan-0.5,namp,-0.5,namp-0.5);
  TH1* hAdcAmpRaw = new TH2F("hAdcAmpRaw","Raw ADC vs Amp Dist;Amplitude (DAC units);ADC",
			     namp,-0.5,namp-0.5,nadc,-0.5,nadc-0.5);
  TH1* hAdcAmpNoNoise = new TH2F("hAdcAmpNoNoise","ADC vs Amp Dist, noisy channels cut;Amplitude (DAC units);ADC",
				 namp,-0.5,namp-0.5,nadc,-0.5,nadc-0.5);

  //TH1* hAmpAdcCutNoNoise = new TH2F("hAmpAdcCutNoNoise","",128,-0.5,127.5,8,-0.5,7.5);
  

  //char goodBco[1000];
  //sprintf(goodBco,"14<=bco&&bco<=16");
  //TCut goodBcoCut = goodBco;

  TCut exclChan = load_chanmask(nevis_cut);

  int bco0 = bco_min; //0; //13;
  int bco1 = bco_max; //2; //128; //15;
  char text[1000];
  sprintf(text,"%d<=bco&&bco<=%d",bco0,bco1);
  TCut bcoCut = text;

  if ( ! nevis_cut ) exclChan = "1==1";
  std::cout << "Channel cut = " << exclChan.GetTitle() << std::endl;

  char cname[1000];
  char title[1000];
  sprintf(cname,"AdcVsAmp_Run%d",runnumber);
  sprintf(title,"ADC vs Amp Run %d",runnumber);
  TCanvas* c3 = new TCanvas(cname,title);
  gPad->SetLogz();
  gPad->SetGridx();
  gPad->SetGridy();
  sprintf(title,"ADC vs. Amp Run %d;Pulse Amplitude (DAC Units);ADC Value",runnumber);
  TH1* hAdcVAmp = new TH2F("hAdcVAmp",title,128,-0.5,127.5,8,-0.5,7.5);
  std::cout << "OK 0 " << std::endl;
  t->Project(hAdcVAmp->GetName(),"adc:amp","amp!=0&&chan!=0"&&bcoCut&&exclChan);
  std::cout << "OK 1 " << std::endl;
  hAdcVAmp->SetStats(0);
  hAdcVAmp->Draw("zcol");

  std::cout << "OK 2 " << std::endl;
  TLatex txt;
  txt.SetNDC(true);
  txt.DrawLatex(0.15,0.85,"Noisy channels removed");
  sprintf(text,"%d \\leq BCO \\leq %d",bco0,bco1);
  txt.DrawLatex(0.15,0.80,text);

  std::cout << "Save canvas " << c3->GetName() << std::endl;
  c3->SaveAs(".png");

  //return;

  // BCO and Channel distributions
  t->Project(hChanRaw->GetName(),"(chan+128*(chip-1)+1664*fpga)");
  t->Project(hBcoRaw->GetName(),"bco");
  t->Project(hBcoChanRaw->GetName(),"bco:(chan+128*(chip-1)+1664*fpga)");

  t->Project(hChanNoNoise->GetName(),"(chan+128*(chip-1)+1664*fpga)",exclChan);
  t->Project(hBcoNoNoise->GetName(),"bco",exclChan);
  t->Project(hBcoChanNoNoise->GetName(),"bco:(chan+128*(chip-1)+1664*fpga)",exclChan);

  // Amplitudes and Channel distributions
  t->Project(hAmpRaw->GetName(),"amp");
  t->Project(hAmpNoNoise->GetName(),"amp",exclChan);
  t->Project(hAdcRaw->GetName(),"adc");
  t->Project(hAdcNoNoise->GetName(),"adc",exclChan);
  t->Project(hAmpChanRaw->GetName(),"amp:(chan+128*(chip-1)+1664*fpga)");
  t->Project(hAmpChanNoNoise->GetName(),"amp:(chan+128*(chip-1)+1664*fpga)",exclChan);
  t->Project(hAdcAmpRaw->GetName(),"adc:amp");
  t->Project(hAdcAmpNoNoise->GetName(),"adc:amp",exclChan);

//   // Use TSpectrum to find peaks in the channel spectrum
//   TH1* ptr = hChanRawNoise;
//   char peaksStr[1000];
//   TPolyMarker* pm = 0;
//   if ( ptr->GetEntries() != 0 ) 
//     {
//       // TSpectrum stupidly executes a Draw() in the process of 
//       // its algorthim.  We create a dummy canvas to allow to do its work w/o
//       // messing up any of our canvases.
//       TCanvas* c1 = new TCanvas();
      
//       gSystem->Load("libSpectrum");
//       TSpectrum sp;
//       sp.SetResolution(3);
//       int npeaks = sp.Search(ptr,4,"nobackground");
//       std::cout << "TSpectrum found " << npeaks << " peaks" << std::endl;
//       TList* fcns = ptr->GetListOfFunctions();
//       pm = (TPolyMarker*)fcns->FindObject("TPolyMarker");
//       if ( pm )
// 	{
// 	  for (int i=0; i<npeaks; i++)
// 	    {
// 	      double x = pm->GetX()[i];
// 	      std::cout << "Peak " << i << " X = " << x << std::endl;
// 	      if ( i == 0 ) sprintf(peaksStr,"(%d-2<=bco&&bco<=%d+2)",x,x);
// 	      else 
// 		sprintf(peaksStr,"%s||(%d-2<=bco&&bco<=%d+2)",peaksStr,x,x);
// 	    }
// 	}
//       delete c1;
//     }
//   else std::cout << "Hist " << ptr->GetName() << " has no entries" << std::endl;
//   TCut peaksCut = peaksStr;
//   std::cout << "Peaks cut = " << peaksCut.GetTitle() << std::endl;

  //char cname[1000];
  sprintf(cname,"BcoChan_Run%d",runnumber);
  sprintf(title,"BCO and Channel Run %d",runnumber);
  TCanvas* c = new TCanvas(cname,title);
  c->Divide(3,2);

  c->cd(1);
  hChanRaw->DrawCopy();
  c->cd(2);
  gPad->SetLogy();
  hBcoRaw->DrawCopy();
  c->cd(3);
  hBcoChanRaw->DrawCopy("zcol");

  c->cd(4);
  hChanNoNoise->DrawCopy();
  c->cd(5);
  gPad->SetLogy();
  hBcoNoNoise->DrawCopy();
  c->cd(6);
  hBcoChanNoNoise->DrawCopy("zcol");

  sprintf(cname,"Amp_Run%d",runnumber);
  sprintf(title,"Amplitude Run %d",runnumber);
  TCanvas* c1 = new TCanvas(cname,title);
  c1->Divide(4,2);

  c1->cd(1);
  hAmpRaw->DrawCopy();
  c1->cd(2);
  hAdcRaw->DrawCopy();
  c1->cd(3);
  hAmpChanRaw->DrawCopy("zcol");
  c1->cd(4);
  hAdcAmpRaw->DrawCopy("zcol");

  c1->cd(5);
  hAmpNoNoise->DrawCopy();
  c1->cd(6);
  hAdcNoNoise->DrawCopy();
  c1->cd(7);
  hAmpChanNoNoise->DrawCopy("zcol");
  c1->cd(8);
  hAdcAmpNoNoise->DrawCopy("zcol");

  sprintf(cname,"Adc_Run%d",runnumber);
  sprintf(title,"ADC Run %d",runnumber);
  TCanvas* c2 = new TCanvas(cname,title);
  //c2->Divide(4,2);

  TLegend* leg = new TLegend(0.5,0.5,0.9,0.8,0,"NDC");
  leg->SetBorderSize(0);
  leg->SetFillStyle(0);
  t->Project(hAmpRaw->GetName(),"amp",exclChan);
  TH1* tmp = hAmpRaw->DrawCopy();
  leg->AddEntry(tmp,"All ADC","L");
  t->Project(hAmpRaw->GetName(),"amp",exclChan&&"adc==0");
  hAmpRaw->SetLineColor(2);
  tmp = hAmpRaw->DrawCopy("same");
  leg->AddEntry(tmp,"ADC = 0","L");
  t->Project(hAmpRaw->GetName(),"amp",exclChan&&"adc>0");
  hAmpRaw->SetLineColor(4);
  tmp = hAmpRaw->DrawCopy("same");
  leg->AddEntry(tmp,"ADC > 0","L");
  leg->Draw();

  c->SaveAs(".png");
  c1->SaveAs(".png");
  c2->SaveAs(".png");
}

TCut
load_chanmask(int cutnum)
{
  char noisyStr[1000];
  if ( cutnum == 1 )
    {
      // The Nevis chip has several really noisy channels.  Eric tells me that 
      // he requested the following channels be bonded out:
      //      16, 17, 47, 48, 70, 79, 96, and 127
      // I later added other observed channels
      const int NUMBAD = 18;
      int noisyChan[NUMBAD] = { 0, 7, 16, 17, 43, 47, 48, 49, 51, 59, 70, 75, 79, 95, 96, 102, 105, 127 };
      for (int i=0; i<NUMBAD; i++)
	{
	  if ( i == 0 ) sprintf(noisyStr,"(chan!=%d)",noisyChan[i]);
	  else 
	    sprintf(noisyStr,"%s&&(chan!=%d)",noisyStr,noisyChan[i]);
	}
    }
  else if ( cutnum == 2 )
    {
      // V2 chip
      //
      int noisyChan[] = { 15, 16, 46, 47, 69, 78, 97, 126 };
      for (unsigned int i=0; i<sizeof(noisyChan)/sizeof(int); i++)
	{
	  if ( i == 0 ) sprintf(noisyStr,"(chan!=%d)",noisyChan[i]);
	  else 
	    sprintf(noisyStr,"%s&&(chan!=%d)",noisyStr,noisyChan[i]);
	}
    }
  else if ( cutnum == 3 )
    {
      // 13 V1 chips on Kapton HDI
      //
      int noisyChan[] = { 271, 1043, 1271, 1413, 1542 };
      for (unsigned int i=0; i<sizeof(noisyChan)/sizeof(int); i++)
	{
	  if ( i == 0 ) sprintf(noisyStr,"((chan+128*(chip-1))!=%d)",noisyChan[i]);
	  else 
	    sprintf(noisyStr,"%s&&((chan+128*(chip-1))!=%d)",noisyStr,noisyChan[i]);
	}
    }
  else
    {
      sprintf(noisyStr,"1==1)");
    }
  TCut exclChan = noisyStr;
  return exclChan;
}
