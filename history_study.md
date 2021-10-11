# Nevis GUIs

## GUI (in the wiki)

## ./nevis_gui_selftrigger
-rwxrwxrwx@ 1 genki  staff   495B  9 29  2016 ./nevis_gui_selftrigger/nevis_gui_diff.txt
-rwxrwxrwx@ 1 genki  staff    32K  4 14  2014 ./nevis_gui_selftrigger/fphxtb.py
-rwxrwxrwx@ 1 genki  staff   3.3K  2 17  2014 ./nevis_gui_selftrigger/comm_panel.py
-rwxrwxrwx@ 1 genki  staff    32K  2 17  2014 ./nevis_gui_selftrigger/fphxtb.py~
-rwxrwxrwx@ 1 genki  staff    92K  2 17  2014 ./nevis_gui_selftrigger/nevis_gui.py


Too old. There is no "Cosmic start" button. No need to merge.

## ./GUI1114  -> 2018?
-rwxrwxrwx  1 genki  staff    19K  9 25  2020 ./GUI1114/read_DAQ.c
-rwxrwxrwx  1 genki  staff    77M 11 14  2018 ./GUI1114/read_DAQ.VC.db
-rwxrwxrwx  1 genki  staff   322B 11 13  2018 ./GUI1114/junk.dat
-rwxrwxrwx  1 genki  staff    92K 10 31  2018 ./GUI1114/nevis_gui_for_SelfTrig.py
-rwxrwxrwx  1 genki  staff   5.7K 10 31  2018 ./GUI1114/read_DAQ.vcxproj
-rwxrwxrwx  1 genki  staff    35K 10 31  2018 ./GUI1114/UpgradeLog2.htm
-rwxrwxrwx  1 genki  staff   1.2K 10 31  2018 ./GUI1114/read_DAQ.vcxproj.filters
-rwxrwxrwx  1 genki  staff    35K 10 31  2018 ./GUI1114/UpgradeLog.htm
-rwxrwxrwx  1 genki  staff   5.0K 10 23  2018 ./GUI1114/comm_panel.pyc
-rwxrwxrwx  1 genki  staff    24K 10 23  2018 ./GUI1114/fphxtb.pyc
-rwxrwxrwx  1 genki  staff    97B 10 23  2018 ./GUI1114/nevis_gui_selftrig.run.cmd
-rwxrwxrwx  1 genki  staff   1.9K 10 23  2018 ./GUI1114/UpgradeLog.XML
-rwxrwxrwx  1 genki  staff   1.1K 10 23  2018 ./GUI1114/UpgradeLog2.XML
-rwxrwxrwx  1 genki  staff   2.2K 10 23  2018 ./GUI1114/UpgradeLog3.XML
-rwxrwxrwx  1 genki  staff   619B 10 23  2018 ./GUI1114/UpgradeLog4.XML
-rwxrwxrwx  1 genki  staff    31K 10 23  2018 ./GUI1114/Wedge112_Bent_Noise.pdf
-rwxrwxrwx  1 genki  staff    13K 10 23  2018 ./GUI1114/Wedge_QA_Fit.C
-rwxrwxrwx  1 genki  staff    26M 10 23  2018 ./GUI1114/read_DAQ.ncb
-rwxrwxrwx  1 genki  staff    61M 10 23  2018 ./GUI1114/read_DAQ.sdf
-rwxrwxrwx  1 genki  staff   887B 10 23  2018 ./GUI1114/read_DAQ.sln

Difference between the original version in the wiki:
```
[genki 18:37:06 nevis_gui] $ diff -rq ../../repo/INTT_Nevis_GUI/GUI GUI1114/ | grep -v -e log -v -e obj -v -e rc -v -e Debug -v -e Release -v -e pyc
Only in GUI1114/: .vs
Only in GUI1114/Backup: .vs
Only in GUI1114/: Backup1
Only in GUI1114/: Backup2
Only in GUI1114/: CDM21228_Setup
Only in GUI1114/: UpgradeLog.htm
Only in GUI1114/: UpgradeLog2.htm
Only in ../../repo/INTT_Nevis_GUI/GUI: debug.pdb
Only in GUI1114/: nevis_gui_for_SelfTrig - コピー.py
Files ../../repo/INTT_Nevis_GUI/GUI/nevis_gui_for_SelfTrig.py and GUI1114/nevis_gui_for_SelfTrig.py differ
Files ../../repo/INTT_Nevis_GUI/GUI/nevis_gui_selftrig.run.cmd and GUI1114/nevis_gui_selftrig.run.cmd differ
Only in GUI1114/: read_DAQ.VC.db
Files ../../repo/INTT_Nevis_GUI/GUI/read_DAQ.c and GUI1114/read_DAQ.c differ
Files ../../repo/INTT_Nevis_GUI/GUI/read_DAQ.vcxproj and GUI1114/read_DAQ.vcxproj differ
```

### nevis_gui_for_SelfTrig - コピー.py
The new file "nevis_gui_for_SelfTrig - コピー.py" is in this directory. Since it's the same as "nevis_gui_for_SelfTrig.py" in the original version, Maybe it's just for a backup...

### nevis_gui_for_SelfTrig.py
Output directory was changed.

### nevis_gui_selftrig.run.cmd
The directory path was changed.

### read_DAQ.c
Changes are mainly related to output to the terminal. The device path "const char* pfi[NCARD]" was also changed. It's good to merge.

```
[genki 18:43:34 nevis_gui] $ diff GUI1114/read_DAQ.c ../../repo/INTT_Nevis_GUI/GUI/read_DAQ.c
310,313d309
<
< 		//sprintf(fileName, "c:/mannel/fphx_raw_%2.2d%2.2d%2.2d-%2.2d%2.2d.dat",
< 			//timeinfo->tm_mday, timeinfo->tm_mon + 1,
< 			//timeinfo->tm_year - 100, timeinfo->tm_hour, timeinfo->tm_min);
321,323d316
< 			time_t nownow = time(&nownow);
< 			struct tm* timeinfo = localtime(&nownow);
<
402c395
< 										printf("data %#x, chip_id %2i chan %3i, adc %i, ampl %i, time %2.2d:%2.2d:%2.2d\n",word, chipid, chan_id, adc, ampl, timeinfo->tm_hour, timeinfo->tm_min, timeinfo->tm_sec);
---
> 										printf("data %#x, chip_id %2i chan %3i, adc %i, ampl %i\n",word, chipid, chan_id, adc, ampl);
536c529
< 	const char* pfi[NCARD] = { "/Dev1/PFI5" };
---
> 	const char* pfi[NCARD] = { "/Dev1/PFI2" };
570,571d562
<
< 		//int32 curTime = clock();
574,579d564
< 		//	double T = (curTime - startTime) / CLOCKS_PER_SEC
< 		//	if (T >= 60.)
< 		//	{
< 		//		take_data = 0;
< 		//		break;
< 			}
```



## ./GUI --> 2018?
-rwxrwxrwx  1 genki  staff   399B 10  1  2020 ./GUI/nevis_gui_selftrig.run.cmd
-rwxrwxrwx  1 genki  staff   322B 10  1  2020 ./GUI/junk.dat
-rwxrwxrwx  1 genki  staff    75M  9 29  2020 ./GUI/read_DAQ.VC.db
-rwxrwxrwx  1 genki  staff    19K  9 25  2020 ./GUI/read_DAQ.c
-rwxrwxrwx  1 genki  staff    93K  7  3  2019 ./GUI/nevis_gui_for_SelfTrig_mod.py
-rwxrwxrwx  1 genki  staff    93K 12 13  2018 ./GUI/nevis_gui_for_SelfTrig.py
-rwxrwxrwx  1 genki  staff   5.7K 10 31  2018 ./GUI/read_DAQ.vcxproj
-rwxrwxrwx  1 genki  staff    35K 10 31  2018 ./GUI/UpgradeLog2.htm
-rwxrwxrwx  1 genki  staff   1.2K 10 31  2018 ./GUI/read_DAQ.vcxproj.filters
-rwxrwxrwx  1 genki  staff    35K 10 31  2018 ./GUI/UpgradeLog.htm
-rwxrwxrwx  1 genki  staff   5.0K 10 23  2018 ./GUI/comm_panel.pyc
-rwxrwxrwx  1 genki  staff    24K 10 23  2018 ./GUI/fphxtb.pyc
-rwxrwxrwx  1 genki  staff   1.9K 10 23  2018 ./GUI/UpgradeLog.XML
-rwxrwxrwx  1 genki  staff   1.1K 10 23  2018 ./GUI/UpgradeLog2.XML
-rwxrwxrwx  1 genki  staff   2.2K 10 23  2018 ./GUI/UpgradeLog3.XML
-rwxrwxrwx  1 genki  staff   619B 10 23  2018 ./GUI/UpgradeLog4.XML
-rwxrwxrwx  1 genki  staff    31K 10 23  2018 ./GUI/Wedge112_Bent_Noise.pdf
-rwxrwxrwx  1 genki  staff    13K 10 23  2018 ./GUI/Wedge_QA_Fit.C
-rwxrwxrwx  1 genki  staff    26M 10 23  2018 ./GUI/read_DAQ.ncb
-rwxrwxrwx  1 genki  staff    61M 10 23  2018 ./GUI/read_DAQ.sdf


### Differences b/w 1114 and GUI
```
[genki 14:48:56 INTT_Nevis_GUI] $ diff -rq GUI/ ../../GUI/nevis_gui/GUI | grep -v -e Debug -v -e   exe
Only in ../../GUI/nevis_gui/GUI: .vs
Files GUI/nevis_gui_for_SelfTrig.py and ../../GUI/nevis_gui/GUI/nevis_gui_for_SelfTrig.py differ
Only in ../../GUI/nevis_gui/GUI: nevis_gui_for_SelfTrig_mod.py
Files GUI/nevis_gui_selftrig.run.cmd and ../../GUI/nevis_gui/GUI/nevis_gui_selftrig.run.cmd differ
Files GUI/read_DAQ.VC.db and ../../GUI/nevis_gui/GUI/read_DAQ.VC.db differ
Files GUI/read_DAQ.c and ../../GUI/nevis_gui/GUI/read_DAQ.c differ
```

#### nevis_gui_for_SelfTrig.py
```
$ diff GUI/nevis_gui_for_SelfTrig.py ../../GUI/nevis_gui/GUI/nevis_gui_for_SelfTrig.py
292c292,310
<
---
>
> def cosmic_start_daq_prog():
> 	send_fo_sync()
> 	send_fpga_reset()
> 	time.sleep(2)
> 	#send_fo_sync()
> 	send_reset(regpanels)
> 	send_init(regpanels)
> 	send_enable_ro(regpanels)
> 	send_latch()
> 	#send_latch()
> 	#send_latch()
> 	send_fem_lvl1_delay(int(fem_lvl1_delay_var.get()))
> 	#send_pulse_module(int(pulse_module_var.get()),int(pulse_wedge_var.get()), f(int(femaddr_var.get())))
> 	send_bco_start()
> 	start_daq_prog(regpanels)
> 	send_self_trig()
> 	#time.sleep(2)
>
640,647c658,665
<              (0x0 << 7) | (0xFF & 20),#   Threshold DAC 0: 00001000
<              (0x0 << 7) | (0xFF & 25),#  Threshold DAC 1: 00010000
<              (0x0 << 7) | (0xFF & 30),#  Threshold DAC 2: 00100000
<              (0x0 << 7) | (0xFF & 35),#  Threshold DAC 3: 01001000
<              (0x0 << 7) | (0xFF & 40),#  Threshold DAC 4: 01010000
<              (0x0 << 7) | (0xFF & 45),# Threshold DAC 5: 01110000
<              (0x0 << 7) | (0xFF & 50),# Threshold DAC 6: 10010000
<              (0x0 << 7) | (0xFF & 176),# Threshold DAC 7: 10110000
---
>              (0x0 << 7) | (0xFF & 10),#   Threshold DAC 0: 00001000
>              (0x0 << 7) | (0xFF & 23),#  Threshold DAC 1: 00010000
>              (0x0 << 7) | (0xFF & 48),#  Threshold DAC 2: 00100000
>              (0x0 << 7) | (0xFF & 98),#  Threshold DAC 3: 01001000
>              (0x0 << 7) | (0xFF & 148),#  Threshold DAC 4: 01010000
>              (0x0 << 7) | (0xFF & 172),# Threshold DAC 5: 01110000
>              (0x0 << 7) | (0xFF & 223),# Threshold DAC 6: 10010000
>              (0x0 << 7) | (0xFF & 248),# Threshold DAC 7: 10110000
953,955c971,973
<                           StringVar(master,'20'),   StringVar(master,'25'),  StringVar(master,'30'),
<                           StringVar(master,'35'),  StringVar(master,'40'),  StringVar(master,'45'),
<                           StringVar(master,'50'), StringVar(master,'176'), StringVar(master,'6'),
---
>                           StringVar(master,'10'),   StringVar(master,'23'),  StringVar(master,'48'),
>                           StringVar(master,'98'),  StringVar(master,'148'),  StringVar(master,'172'),
>                           StringVar(master,'223'), StringVar(master,'248'), StringVar(master,'6'),
1942c1960,1965
<     b.config(command=lambda : send_self_trig())
---
>     b.config(command=lambda : send_self_trig())
>
>     b = Button(ops_frame,text="Cosmic Start",width=10,bg='white',fg='black')
>     b.grid(row=4,column=col)
>     b.config(command=lambda : cosmic_start_daq_prog())
>     col += 1
```


The button "Cosmic Start" was equipped.

#### nevis_gui_for_SelfTrig_mod.py
Newly made. The differences b/w nevis_gui_for_SelfTrig.py and nevis_gui_for_SelfTrig_mod.py are:
```
$ diff ../../GUI/nevis_gui/GUI/nevis_gui_for_SelfTrig.py ../../GUI/nevis_gui/GUI/nevis_gui_for_SelfTrig_mod.py
1851c1851
<     moduleid = [ 15, 0, 1 ]
---
>     moduleid = [ 15, 0, 1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 13, 14 ]
```

#### nevis_gui_selftrig.run.cmd
This file was updated on 2020/Sep/30 by G. Nukazuka. I think this is the only file updated later than 2018.
The change is just to set the directory path used at that time. 
```
$ diff GUI/nevis_gui_selftrig.run.cmd ../../GUI/nevis_gui/GUI/nevis_gui_selftrig.run.cmd
1,2c1,8
< cd C:\Users\sphenix\Documents\INTT_testbench\GUI_BNL\GUI
< cmd /k python nevis_gui_for_SelfTrig.py
\ No newline at end of file
---
> rem Move to the directory where the GUI script is
> rem 2020/Sep/30 New version of the GUI to save data like "nwu_fphx_raw_..."
> rem is launched. (G. Nukazuka, genki.nukazuka@riken.jp)
> rem cd C:\Users\sphenix\Documents\INTT_testbench\GUI_BNL\GUI
> rem cmd /k python nevis_gui_for_SelfTrig.py
>
> cd C:\Users\sphenix\Documents\INTT_testbench\GUI_BNL\GUI20200929
> cmd /k python nevis_gui_for_source.py
```

#### read_DAQ.c
The updates are for online monitoring in the terminal. They are not so important.

```
$ diff GUI/read_DAQ.c ../../GUI/nevis_gui/GUI/read_DAQ.c
310,313d309
<
< 		//sprintf(fileName, "c:/mannel/fphx_raw_%2.2d%2.2d%2.2d-%2.2d%2.2d.dat",
< 			//timeinfo->tm_mday, timeinfo->tm_mon + 1,
< 			//timeinfo->tm_year - 100, timeinfo->tm_hour, timeinfo->tm_min);
321,323d316
< 			time_t nownow = time(&nownow);
< 			struct tm* timeinfo = localtime(&nownow);
<
402c395
< 										printf("data %#x, chip_id %2i chan %3i, adc %i, ampl %i, time %2.2d:%2.2d:%2.2d\n",word, chipid, chan_id, adc, ampl, timeinfo->tm_hour, timeinfo->tm_min, timeinfo->tm_sec);
---
> 										printf("data %#x, chip_id %2i chan %3i, adc %i, ampl %i\n",word, chipid, chan_id, adc, ampl);
570d562
<
574,579c566,570
< 		//	double T = (curTime - startTime) / CLOCKS_PER_SEC
< 		//	if (T >= 60.)
< 		//	{
< 		//		take_data = 0;
< 		//		break;
< 			}
---
> 			//if ((curTime - startTime)/CLOCKS_PER_SEC> 60) /*�ǉ�����*/
> 			//{
> 			//	take_data = 0;
> 			//	break;
> 			//}
582a574,575
>
>
```

## ./GUI0729  -> 2019?
-rwxrwxrwx  1 genki  staff   404B 10  1  2020 ./GUI0729/nevis_gui_selftrig.run.cmd
-rwxrwxrwx  1 genki  staff   322B 10  1  2020 ./GUI0729/junk.dat
-rwxrwxrwx  1 genki  staff    19K  9 25  2020 ./GUI0729/read_DAQ.c
-rwxrwxrwx  1 genki  staff    95K  7 29  2020 ./GUI0729/nevis_gui_for_SelfTrig_20200729.py
-rwxrwxrwx  1 genki  staff    77M 12 16  2019 ./GUI0729/read_DAQ.VC.db
-rwxrwxrwx  1 genki  staff    86K  7 29  2019 ./GUI0729/nevis_gui_for_SelfTrig.pyc
-rwxrwxrwx  1 genki  staff    94K  7 29  2019 ./GUI0729/nevis_gui_for_SelfTrig.py
-rwxrwxrwx  1 genki  staff    93K  7  3  2019 ./GUI0729/nevis_gui_for_SelfTrig_mod.py
-rwxrwxrwx  1 genki  staff   5.7K 10 31  2018 ./GUI0729/read_DAQ.vcxproj
-rwxrwxrwx  1 genki  staff    35K 10 31  2018 ./GUI0729/UpgradeLog2.htm
-rwxrwxrwx  1 genki  staff   1.2K 10 31  2018 ./GUI0729/read_DAQ.vcxproj.filters
-rwxrwxrwx  1 genki  staff    35K 10 31  2018 ./GUI0729/UpgradeLog.htm
-rwxrwxrwx  1 genki  staff   5.0K 10 23  2018 ./GUI0729/comm_panel.pyc
-rwxrwxrwx  1 genki  staff    24K 10 23  2018 ./GUI0729/fphxtb.pyc
-rwxrwxrwx  1 genki  staff   1.9K 10 23  2018 ./GUI0729/UpgradeLog.XML
-rwxrwxrwx  1 genki  staff   1.1K 10 23  2018 ./GUI0729/UpgradeLog2.XML
-rwxrwxrwx  1 genki  staff   2.2K 10 23  2018 ./GUI0729/UpgradeLog3.XML
-rwxrwxrwx  1 genki  staff   619B 10 23  2018 ./GUI0729/UpgradeLog4.XML
-rwxrwxrwx  1 genki  staff    31K 10 23  2018 ./GUI0729/Wedge112_Bent_Noise.pdf
-rwxrwxrwx  1 genki  staff    13K 10 23  2018 ./GUI0729/Wedge_QA_Fit.C

./GUI20200929
-rwxrwxrwx  1 genki  staff    96K  7  7 13:25 ./GUI20200929/nevis_gui_for_calib.py
-rwxrwxrwx  1 genki  staff    96K  5 21 16:32 ./GUI20200929/nevis_gui_for_source.py
-rwxrwxrwx  1 genki  staff   398B  3 30  2021 ./GUI20200929/junk.dat
-rwxrwxrwx  1 genki  staff    96K  3 29  2021 ./GUI20200929/nevis_gui_for_calib.py~
-rwxrwxrwx  1 genki  staff    24K  3 26  2021 ./GUI20200929/fphxtb.pyc
-rwxrwxrwx  1 genki  staff    12K  3 26  2021 ./GUI20200929/.fphxtb.py.un~
-rwxrwxrwx  1 genki  staff    32K  3 26  2021 ./GUI20200929/fphxtb.py
-rwxrwxrwx  1 genki  staff    87M  2 10  2021 ./GUI20200929/read_DAQ.VC.db
-rwxrwxrwx  1 genki  staff    32K 12 21  2020 ./GUI20200929/fphxtb.py~
-rwxrwxrwx  1 genki  staff   124K 12 12  2020 ./GUI20200929/.nevis_gui_for_calib2.py.un~
-rwxrwxrwx  1 genki  staff    97K 12 12  2020 ./GUI20200929/nevis_gui_for_calib2.py
-rwxrwxrwx  1 genki  staff    97K 12 12  2020 ./GUI20200929/nevis_gui_for_calib2.py~
-rwxrwxrwx  1 genki  staff   405B 12  9  2020 ./GUI20200929/nevis_gui_selftrig2.run.cmd
-rwxrwxrwx  1 genki  staff     1B 12  9  2020 ./GUI20200929/packet.dat
-rwxrwxrwx  1 genki  staff     1B 12  9  2020 ./GUI20200929/packet.dat.bak
-rwxrwxrwx  1 genki  staff   3.7K 12  9  2020 ./GUI20200929/.nevis_gui_for_calib.py.un~
-rwxrwxrwx  1 genki  staff   524B 12  9  2020 ./GUI20200929/.packet.dat.un~
-rwxrwxrwx  1 genki  staff     3B 12  9  2020 ./GUI20200929/packet.dat~
-rwxrwxrwx  1 genki  staff    26K 12  6  2020 ./GUI20200929/read_DAQ.c
-rwxrwxrwx  1 genki  staff   410B 11 30  2020 ./GUI20200929/nwu_fphx_raw_20201130-1516_0.root


./20210327
-rw-r--r--@ 1 genki  staff   6.0K  6  1 14:14 ./20210327/.DS_Store
-rw-r--r--@ 1 genki  staff    92K  3 27  2021 ./20210327/nevis_gui.py
-rw-r--r--@ 1 genki  staff    92K 10 22  2013 ./20210327/nevis_gui.py~

./GUI20210721_for_sharing
-rw-r--r--@ 1 genki  staff   6.0K  7 21 17:30 ./GUI20210721_for_sharing/.DS_Store
-rwxrwxrwx  1 genki  staff   5.9K  7 21 17:26 ./GUI20210721_for_sharing/README.md
-rwxrwxrwx  1 genki  staff    90K  7 21 16:30 ./GUI20210721_for_sharing/nevis_gui_for_calib.py
-rwxrwxrwx  1 genki  staff    23K  2 12  2021 ./GUI20210721_for_sharing/check_chip_prototypeMaximam6.c

./GUI20210802_Readbacker
-rwxrwxrwx  1 genki  staff   6.1K  8  2 14:08 ./GUI20210802_Readbacker/README.md
-rwxrwxrwx  1 genki  staff   954B  8  2 14:07 ./GUI20210802_Readbacker/junk.dat
-rwxrwxrwx  1 genki  staff   106K  8  2 13:56 ./GUI20210802_Readbacker/nevis_gui_for_calib.py
-rwxrwxrwx  1 genki  staff    26K  6 23 16:59 ./GUI20210802_Readbacker/fphxtb.pyc
-rwxrwxrwx  1 genki  staff    36K  6 23 16:11 ./GUI20210802_Readbacker/fphxtb.py
-rwxrwxrwx  1 genki  staff   5.1K  6  9 20:47 ./GUI20210802_Readbacker/comm_panel.pyc
-rwxrwxrwx  1 genki  staff   3.6K 10 23  2018 ./GUI20210802_Readbacker/comm_panel.py


./GUI20200929_20210529
-rwxrwxrwx  1 genki  staff   100K  6 10 11:16 ./GUI20200929_20210529/nevis_gui_for_calib.py
-rwxrwxrwx  1 genki  staff   100K  5 29 10:00 ./GUI20200929_20210529/nevis_gui_for_calib.py~


