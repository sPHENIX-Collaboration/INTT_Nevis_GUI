#include <cstdio>
#include <iomanip>

int getFileSize(std::ifstream& s);

void plot_calib_4modules(char* fname = "C:/FVTX/data_0", int maxbuf = 0, int n_meas = 64, float maxscale = 200.)
{
	gStyle->SetPalette(1);
	gStyle->SetOptFit(1);
	gStyle->SetOptStat(0);
	gStyle->SetFrameFillColor(0);  
	gStyle->SetTitleFontSize(0.1);

	char cf_name[100];
	unsigned long int dataIn[1000000];
	long lSize;
	size_t result;

	int bco, adc, ampl, col_raw, col, chip_id, fpga_id, module, mchip;
	int chan_id, n_hits;

	FILE* cal_file;

	int NCHAN = 128;
	int NMODULES = 4;
	int NCHIPS = 8;

	TNtuple *hits = new TNtuple("hits","test","chan_id:ampl:adc:bco:rawchip:event:fpga:module:chip");

	TH2F* h1[32];
    char* histname = new char[10];
    char* title = new char[20];
	for (int imod = 0; imod < NMODULES; imod++){
      for (int ichip=0; ichip< NCHIPS; ichip++){
	      sprintf(histname,"h1_%i",imod*NCHIPS+ichip);
		  sprintf(title, "Module %i, Chip %i", imod, ichip+1);
          h1[imod*NCHIPS + ichip] = new TH2F(histname, title, 128,-0.5,127.5,64,-0.5,63.5);
  	      h1[imod*NCHIPS + ichip]->SetMaximum(maxscale);
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
	int nhits[128][1024];

	for (int ichan=0; ichan<NCHAN; ichan++)
		for (int iamp = 0; iamp < n_meas; iamp ++) nhits[chan_id][iamp] = 0;

	// Extract bco, channel, amplitude, and adc from each hit, and count the number of 
	// hits at each amplitude for each channel:

	int ievent = 0;
    int bufcnt = 0;
	int found[13] = {0};
    int chipnotfound[13] = {0};
    int countchips = 0;

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
			unsigned char* p2 = &p[n];
			for(int n=0; n<16; n++)
			{
				std::cout << "      Reg " << n << ": " << (int) p2[n] << std::endl;
			}
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
			if (bufcnt < 10) std::cout << "Buffer " << bufcnt << ": Data record, "
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
		  fpga_id = (data[index]&0x80)>>7;
		  ampl = (data[index]&0x7e0000)>>17;

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
		    bco = ((data[index] & 0x200) >> 3) | ((data[index] & 0x1f800000) >> 23);
		    chan_id = ((data[index] & 0x100) >> 2) | ((data[index] & 0xfc00) >> 10);
		    adc = (data[index] & 0x2 << 1) | ((data[index] & 0xc0000000) >> 30);
		  }

		  nhits[chan_id][ampl]++;

		  if (ievent < 10) cout<< "Raw data = " << hex << data[index]
		                   <<", chip_id =  " << chip_id << ", chan_id =  " <<c han_id
						   <<", bco = " << bco << ", ampl = " << ampl
						   <<", fpga = " << fpga_id << endl;

		  hits->Fill(chan_id, ampl, adc, bco, chip_id, ievent, fpga_id, module, mchip);

		  //Note:  we seem to get some odd chip_ids out of the new DAQ VHDL code
		  //after the event gets larger than some value.  Need to understand this:
		  if (bco==0 && mchip>0 && mchip<9){
			  h1[(int)((module)*NCHIPS + mchip-1)]->Fill(chan_id,ampl);
		  }

		  ievent++;
		}
	    //if ( checksum != data[index] ) 
	    //std::cout << "WARNING: bad checksum = "
		//      << std::hex << checksum << std::dec << std::endl;
#ifdef OLD
			index = start + cnt + 2;
#else
			index = start + cnt;
#endif

	  }  // if block on record type
	}  //Loop over data


	TCanvas *c1 = new TCanvas("c1","Amplitude vs. Channel",50,50,1200,800);
	
	
	c1->Divide(8,4);
	c1->Draw();
	

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
  	c1->cd(14);
        h1[13]->Draw("color4z");
  	c1->cd(15);
        h1[14]->Draw("color4z");
  	c1->cd(16);
        h1[15]->Draw("color4z");
	c1->cd(17);
        h1[16]->Draw("color4z");
  	c1->cd(18);
        h1[17]->Draw("color4z");
  	c1->cd(19);
        h1[18]->Draw("color4z");
  	c1->cd(20);
        h1[19]->Draw("color4z");
  	c1->cd(21);
        h1[20]->Draw("color4z");
  	c1->cd(22);
        h1[21]->Draw("color4z");
  	c1->cd(23);
        h1[22]->Draw("color4z");
  	c1->cd(24);
        h1[23]->Draw("color4z");
  	c1->cd(25);
        h1[24]->Draw("color4z");
  	c1->cd(26);
        h1[25]->Draw("color4z");
  	c1->cd(27);
        h1[26]->Draw("color4z");
  	c1->cd(28);
        h1[27]->Draw("color4z");
  	c1->cd(29);
        h1[28]->Draw("color4z");
  	c1->cd(30);
        h1[29]->Draw("color4z");
  	c1->cd(31);
        h1[30]->Draw("color4z");
  	c1->cd(32);
        h1[31]->Draw("color4z");

	float mrgn = 0.06;
	float pdmrgn = 0.00;
	for (int dex=1; dex<17; dex++)
	{
	c1->cd(dex);
	c1->GetPad(dex)->SetBottomMargin(mrgn);
	c1->GetPad(dex)->SetTopMargin(mrgn);
	c1->GetPad(dex)->SetLeftMargin(mrgn);
	c1->GetPad(dex)->SetRightMargin(mrgn);
	};

	gStyle->SetPadTopMargin(pdmrgn);
	gStyle->SetPadLeftMargin(pdmrgn);
	gStyle->SetPadBottomMargin(pdmrgn);
	gStyle->SetPadRightMargin(pdmrgn);

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