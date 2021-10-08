
AUTOMAKE_OPTIONS = foreign

# List of shared libraries to produce

lib_LTLIBRARIES = libtest_clustering.la

ROOTCFLAGS = $(shell root-config --cflags)

#AM_LDFLAGS = -L$(libdir) -L$(OFFLINE_MAIN)/lib

AM_CPPFLAGS =-I$(includedir) -I$(OFFLINE_MAIN)/include -I$(ROOTSYS)/include

##############################################
# please add new classes in alphabetical order

include_HEADERS = 

##############################################
# please add new classes in alphabetical order

libtest_clustering_la_SOURCES = \
  Clustering.C

libtest_clustering_la_LIBADD = \
  -L$(libdir) \
  -L$(OFFLINE_MAIN)/lib \
  @ROOTLIBS@

BUILT_SOURCES = \
  testexternals.C

noinst_PROGRAMS = \
  testexternals

bin_PROGRAMS = get_raw_events read_DAQ

testexternals_SOURCES = \
  testexternals.C

testexternals_LDADD = \
  libtest_clustering.la

get_raw_events_SOURCES = get_raw_events.C
get_raw_events_LDADD = libtest_clustering.la

# This is really hacky and won't work on your system.  I built and installed by hand
# the boost libs on fedora 11.  Problem is that I had to use gcc34 to be compatible
# with the PHENIX software.  I had to bend over backward to get boost 1.38 to build
# with a non-default compiler, and I don't think it finished 100%.
read_DAQ_CPPFLAGS = -x c++ -I$(includedir)/boost
read_DAQ_LDFLAGS = -L$(libdir) -lboost_thread-gcc34-mt -lboost_system-gcc34-mt
read_DAQ_SOURCES = read_DAQ.c

testexternals.C:
	echo "//*** this is a generated file. Do not commit, do not edit" > $@
	echo "int main()" >> $@
	echo "{" >> $@
	echo "  return 0;" >> $@
	echo "}" >> $@

clean-local:
	rm -f *Dict* $(BUILT_SOURCES)

%Dict.C : %.h %LinkDef.h
	rootcint -f $@ -c -D__linux__ $(DEFAULT_INCLUDES) $(INCLUDES) $^
