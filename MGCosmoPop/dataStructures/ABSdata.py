#!/usr/bin/env python3
#    Copyright (c) 2021 Michele Mancarella <michele.mancarella@unige.ch>
#
#    All rights reserved. Use of this source code is governed by a modified BSD
#    license that can be found in the LICENSE file.

from abc import ABC, abstractmethod
from scipy.stats import ks_2samp
import numpy as np
from scipy.integrate import cumtrapz
from scipy.interpolate import interp1d
import astropy.units as u
import os


class Data(ABC):
    
    def __init__(self, ):
        pass
        
    @abstractmethod
    def _load_data(self):
        pass
    
    @abstractmethod
    def get_theta(self):
        pass
    
    def downsample(self, nSamples=None, percSamples=None, verbose=True):
        if nSamples is None:
            return self._downsample_perc(percSamples, verbose=verbose)
        elif percSamples is None:
            return self._downsample_n(nSamples, verbose=verbose)
        else:
            raise ValueError('One among nSamples and percSamples should not be None')

    def _downsample_perc(self, percSamples, verbose=True):
        try:
            samples = np.array([self.m1z, self.m2z, self.dL, *self.spins ])#self.Nsamples                                       
        except:
            print('No spins in this data')
            samples = np.array([self.m1z, self.m2z, self.dL])
        Npar = samples.shape[0]
        print('Npar: %s' %Npar)
        Nobs = samples.shape[1]
        print('Nobs in downsample: %s' %Nobs)
        print('Reducing all samples by %s percent' %(percSamples*100))
        self.Nsamples = (np.array(self.Nsamples)*percSamples).astype(int)
        self.logNsamples=np.log(self.Nsamples)
        maxNsamples = self.Nsamples.max()
        m1zD, m2zD, dLD,  = np.full((Nobs,maxNsamples), np.nan), np.full((Nobs,maxNsamples), np.nan), np.full((Nobs,maxNsamples), np.nan) #np.zeros((Nobs,maxNsamples)), np.zeros((Nobs,maxNsamples)), np.zeros((Nobs,maxNsamples))
        if Npar==5:
            s0D, s1D = np.full((Nobs,maxNsamples), np.nan), np.full((Nobs,maxNsamples), np.nan)#np.zeros((Nobs,nSamples)), np.zeros((Nobs,nSamples))
        for o in range(Nobs):
            if Npar==5:
                m1zD[o, :self.Nsamples[o]], m2zD[o, :self.Nsamples[o]], dLD[o, :self.Nsamples[o]], s0D[o, :self.Nsamples[o]], s1D[o, :self.Nsamples[o]] = self._downsample(samples[:,o, :], self.Nsamples[o], verbose=verbose)
            elif Npar==3:
                m1zD[o, :self.Nsamples[o]], m2zD[o, :self.Nsamples[o]], dLD[o, :self.Nsamples[o]] = self._downsample(samples[:,o, :], self.Nsamples[o], verbose=verbose)
        if Npar==5:
            self.spins = [s0D, s1D]

        self.m1z = m1zD
        self.m2z = m2zD
        self.dL = dLD


    def _downsample_n(self, nSamples, verbose=True):
        
        try:
            samples = np.array([self.m1z, self.m2z, self.dL, *self.spins ])#self.Nsamples
        except:
            print('No spins in this data')
            samples = np.array([self.m1z, self.m2z, self.dL])
        Npar = samples.shape[0]
        print('Npar: %s' %Npar)
        Nobs = samples.shape[1]
        
        print('Nobs in downsample: %s' %Nobs)
        m1zD, m2zD, dLD,  = np.zeros((Nobs,nSamples)), np.zeros((Nobs,nSamples)), np.zeros((Nobs,nSamples)), #np.zeros((Nobs,nSamples)), np.zeros((Nobs,nSamples))
        if Npar==5:
            s0D, s1D = np.zeros((Nobs,nSamples)), np.zeros((Nobs,nSamples))
        for o in range(Nobs):
            if Nobs>200:
                if o>0:
                    verbose=False
            if Npar==5:
                m1zD[o], m2zD[o], dLD[o], s0D[o], s1D[o] = self._downsample(samples[:,o, :], nSamples, verbose=verbose)
            elif Npar==3:
                m1zD[o], m2zD[o], dLD[o] = self._downsample(samples[:,o, :], nSamples, verbose=verbose)
        if Npar==5:
            self.spins = [s0D, s1D]
                
        self.m1z = m1zD
        self.m2z = m2zD
        self.dL = dLD

        self.logNsamples=np.where(self.logNsamples<np.log(nSamples), self.logNsamples, np.log(nSamples)) #np.full(Nobs, np.log(nSamples))
        self.Nsamples=np.where(np.array(self.Nsamples)<nSamples, self.Nsamples, nSamples)

    def _downsample(self, posterior, nSamples,  verbose=True):
        
        if nSamples is None:
            return posterior
        if verbose:
            print('Downsampling posterior to %s samples...' %nSamples)
        
        posterior = np.array(posterior)
        #nparams=posterior.shape[0]
        nOrSamples=(~np.isnan(posterior)[0]).sum()
        if verbose:
            print('Number of original samples: %s '%nOrSamples)
        #print('posterior shape: %s' %str(posterior.shape))
        if len(posterior) == 1:
            if verbose:
                print('Using inverse sampling method')
            n, bins = np.histogram(posterior, bins=50)
            n = np.array([0] + [i for i in n])
            cdf = cumtrapz(n, bins, initial=0)
            cdf /= cdf[-1]
            icdf = interp1d(cdf, bins)
            samples = icdf(np.random.rand(nSamples))
        else:
            if nOrSamples<nSamples:
                nans_to_fill = nSamples-nOrSamples
                if verbose:
                    print('Using all original samples and filling with %s nans' %nans_to_fill)
                samples = []
                for i,p in enumerate(posterior):
                    #print(i)
                    #print('p shape: %s' %str(p.shape))
                    or_samples_position =  ~np.isnan(p)
                    new_p = np.concatenate([p[or_samples_position], np.full( nans_to_fill, np.nan)])
                    assert np.isnan(new_p).sum()==nans_to_fill
                    samples.append(new_p)
            else:
                if verbose:
                    print('Randomly choosing subset of samples')
                keep_idxs = np.random.choice(nOrSamples, nSamples, replace=False)
                #samples = [i[keep_idxs] for i in posterior]
                samples=[]
                for i, p in enumerate(posterior):
                    or_samples_position =  ~np.isnan(p)
                    or_samples = p[or_samples_position]
                    #keep_idxs = np.random.choice(nOrSamples, nSamples, replace=False)
                    assert ~np.any(np.isnan(or_samples[keep_idxs]))
                    samples.append(or_samples[keep_idxs])
                #print(len(samples))
        #print(samples[0].shape)
        return samples
    
    
    
    
class LVCData(Data):
    
    def __init__(self, fname, nObsUse=None, nSamplesUse=None, percSamplesUse=None, dist_unit=u.Gpc, events_use=None, which_spins='chiEff', SNR_th=8., FAR_th=1. ):
        
        Data.__init__(self)
        
        self.FAR_th = FAR_th
        self.SNR_th = SNR_th
        print('FAR th in LVC data: %s' %self.FAR_th)
        self.events_use=events_use
        self.which_spins=which_spins
        
        nObsUse=None
        if events_use is not None:
            if events_use['use'] is not None:
                nObsUse=len(events_use['use'])
        
        self.dist_unit = dist_unit
        self.events = self._get_events(fname, events_use)
        
        self.m1z, self.m2z, self.dL, self.spins, self.Nsamples = self._load_data(fname, nObsUse, which_spins=which_spins)  
        self.Nobs=self.m1z.shape[0]
        #print('We have %s observations' %self.Nobs)
        print('Number of samples for each event: %s' %self.Nsamples )
        self.logNsamples = np.log(self.Nsamples)

        if nSamplesUse is not None or percSamplesUse is not None:
            self.downsample(nSamples=nSamplesUse, percSamples=percSamplesUse)
            print('Number of samples for each event after downsamplng: %s' %self.Nsamples )
            

        #assert (self.m1z >= 0).all()
        #assert (self.m2z >= 0).all()
        #assert (self.dL >= 0).all()
        #assert(self.m2z<=self.m1z).all()
        
        # The first observing run (O1) ran from September 12th, 2015 to January 19th, 2016 --> 129 days
        # The second observing run (O2) ran from November 30th, 2016 to August 25th, 2017 --> 267 days
        self._set_Tobs() #Tobs=  (129+267)/365. # yrs
        
        print('Obs time (yrs): %s' %self.Tobs )
        
        self.Nobs=self.m1z.shape[0]
    
    @abstractmethod
    def _name_conditions(self, f ):
        pass
    
    @abstractmethod
    def _set_Tobs(self):
        pass
    
    @abstractmethod
    def _get_not_BBHs(self):
        pass

    @abstractmethod
    def _load_data_event(self, **kwargs):
        pass
    
    
    def get_theta(self):
        return np.array( [self.m1z, self.m2z, self.dL , self.spins ] )  
    
    @abstractmethod
    def _get_name_from_fname(self, fname):
        pass
    
    
    def _get_events(self, fname, events_use, ):
        
        
        allFiles = [f for f in os.listdir(fname) if f.endswith(self.post_file_extension)] #glob.glob(os.path.join(fname, '*.h5' ))
        #print(allFiles)
        elist = [self._get_name_from_fname(f) for f in allFiles if self._name_conditions(f) ]
        
        
        # Exclude events not identified as BBHs
        list_BBH_or = [x for x in elist if x not in self._get_not_BBHs() ]
        print('In the '+fname.split('/')[-1]+' data we have the following BBH events, total %s (excluding %s):' %(len(list_BBH_or) ,str(self._get_not_BBHs())) )
        print(list_BBH_or)
        
        # Impose cut on SNR
        print('Using only events with SNR>%s (round to 1 decimal digit)' %self.SNR_th)
        list_BBH_0 = [x for x in list_BBH_or if np.round(self.metadata[self.metadata.commonName==x].network_matched_filter_snr.values, 1)>=self.SNR_th  ]
        list_BBH_excluded_0 = [(x, np.round(self.metadata[self.metadata.commonName==x].network_matched_filter_snr.values), 1)[0] for x in list_BBH_or if np.round(self.metadata[self.metadata.commonName==x].network_matched_filter_snr.values, 1)<self.SNR_th  ]
        print('Excluded the following events with SNR<%s: ' %self.SNR_th)
        print(list_BBH_excluded_0)
        print('%s events remaining.' %len(list_BBH_0))

        # Impose cut on FAR
        print('Using only events with FAR<%s' %self.FAR_th)
        list_BBH = [x for x in list_BBH_0 if self.metadata[self.metadata.commonName==x].far.values<=self.FAR_th  ]
        list_BBH_excluded = [(x, self.metadata[self.metadata.commonName==x].far.values) for x in list_BBH_0 if self.metadata[self.metadata.commonName==x].far.values>self.FAR_th  ]
        print('Excluded the following events with FAR>%s: ' %self.FAR_th)
        print(str(list_BBH_excluded))
        print('%s events remaining.' %len(list_BBH))
        

        
        # Exclude other events if this is required in the config file
        if events_use is not None and events_use['use'] is not None and events_use['not_use'] is not None:
            raise ValueError('You passed options to both use and not_use. Please only provide the list of events that you want to use, or the list of events that you want to exclude. ')
        elif events_use is not None and events_use['use'] is not None:
            # Use only events given in use
            print('Using only BBH events : ')
            print(events_use['use'])
            list_BBH_final = [x for x in list_BBH if x in events_use['use']]
        elif events_use is not None and events_use['not_use'] is not None:
            print('Excluding BBH events : ')
            print(events_use['not_use'])
            list_BBH_final = [x for x in list_BBH if x not in events_use['not_use']]
        else:
            print('Using all BBH events')
            list_BBH_final=list_BBH
        
        

        return list_BBH_final
 
    
    def _load_data(self, fname, nObsUse, which_spins='chiEff'):
        print('Loading data...')
    
        
        #events = self._get_events_names(fname)
        if nObsUse is None:
            nObsUse=len(self.events)
            
        
        #print('We have the following events: %s' %str(events))
        m1s, m2s, dLs, spins = [], [], [], []
        allNsamples=[]
        for event in self.events[:nObsUse]:
                print('Reading data from %s' %event)
            #with h5py.File(fname, 'r') as phi:
                m1z_, m2z_, dL_, spins_  = self._load_data_event(fname, event, nSamplesUse=None, which_spins=which_spins)
                print('Number of samples in LVC data: %s' %m1z_.shape[0]) #%(~np.isnan(m1z_)).sum()) #%m1z_.shape[0])
                m1s.append(m1z_)
                m2s.append(m2z_)
                dLs.append(dL_)
                spins.append(spins_)
                assert len(m1z_)==len(m2z_)
                assert len(m2z_)==len(dL_)
                if which_spins!="skip":
                    assert len(spins_)==2
                    assert len(spins_[0])==len(dL_)
                else:  assert spins_==[]
                
                nSamples = len(m1z_)
                
                allNsamples.append(nSamples)
            #print('ciao')
        print('We have %s events.'%len(allNsamples))
        max_nsamples = max(allNsamples) 
        
        fin_shape=(nObsUse, max_nsamples)
        
        m1det_samples= np.full(fin_shape, np.NaN)  #np.zeros((len(self.events),max_nsamples))
        m2det_samples=np.full(fin_shape, np.NaN)
        dl_samples= np.full(fin_shape, np.NaN)
        if which_spins!="skip":
            spins_samples= [np.full(fin_shape, np.NaN), np.full(fin_shape, np.NaN) ]
        else: spins_samples=[]
        
        for i in range(nObsUse):
            
            m1det_samples[i, :allNsamples[i]] = m1s[i]
            m2det_samples[i, :allNsamples[i]] = m2s[i]
            dl_samples[i, :allNsamples[i]] = dLs[i]
            if which_spins!="skip":
                spins_samples[0][i, :allNsamples[i]] = spins[i][0]
                spins_samples[1][i, :allNsamples[i]] = spins[i][1]
        
        if self.dist_unit==u.Gpc:
            print('Using distances in Gpc')   
            dl_samples*=1e-03
        
        return m1det_samples, m2det_samples, dl_samples, spins_samples, allNsamples
    
    
    def logOrMassPrior(self):
        return np.zeros(self.m1z.shape)

    def logOrDistPrior(self):
        # dl^2 prior on dL
        return np.where( ~np.isnan(self.dL), 2*np.log(self.dL), 0)
    
  
  

  
