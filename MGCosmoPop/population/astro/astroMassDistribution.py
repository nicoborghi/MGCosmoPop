#!/usr/bin/env python3
#    Copyright (c) 2021 Michele Mancarella <michele.mancarella@unige.ch>
#
#    All rights reserved. Use of this source code is governed by a modified BSD
#    license that can be found in the LICENSE file.

from ..ABSpopulation import BBHDistFunction
import numpy as np
import scipy.stats as ss
from scipy.integrate import cumtrapz

import sys
import os

PACKAGE_PARENT = '../..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

import utils



########################################################################
# MASS DISTRIBUTION
########################################################################



class AstroSmoothPowerLawMass(BBHDistFunction):
    
    '''
    Mass distribution  - Power law with smooth transition to zero at the edges; from 1908.09084
    '''
    
    
    def __init__(self, normalization='integral' ):
        
        BBHDistFunction.__init__(self)
        
        self.normalization=normalization
        print('Normalization of the mass function: %s' %normalization)
        self.params = ['alpha', 'beta', 'ml', 'sl', 'mh', 'sh' ]
        
        self.baseValues = {
                           
                           'alpha':0.75,
                           'beta':0.0, 
                           'ml':5.0, 
                           'sl':0.1, 
                           'mh':45.0,
                           'sh':0.1}
        
        self.names = {
                           'alpha':r'$\alpha$',
                           'beta':r'$\beta$', 
                           'ml':r'$M_l$', 
                           'sl':r'$\sigma_l$', 
                           'mh':r'$M_h$',
                           'sh':r'$\sigma_h$'}
         
        self.n_params = len(self.params)
    
    def _logpdfm1only(self, m1, alpha, ml, sl, mh, sh ):
        
        logp = np.log(m1)*(-alpha)+self._logf_smooth(m1, ml=ml, sl=sl, mh=mh, sh=sh)
        
        return logp
    
    
    
    def _logpdfm1(self, m1, alpha, ml, sl, mh, sh ):
        '''Marginal prob. '''
        
        logp = np.log(m1)*(-alpha)+self._logf_smooth(m1, ml=ml, sl=sl, mh=mh, sh=sh)
        
        return logp
    
    def _logpdfm2(self, m2, beta, ml, sl, mh, sh ):
        
        logp = np.log(m2)*(beta)+self._logf_smooth(m2, ml=ml, sl=sl, mh=mh, sh=sh)
        
        return logp
    
    
    def logpdf(self, theta, lambdaBBHmass):
        
        '''p(m1, m2 | Lambda ), normalized to one'''
        
        m1, m2 = theta
        alpha, beta, ml, sl, mh, sh = lambdaBBHmass
        
        logpdfMass = self._logpdfm1only(m1,alpha, ml, sl, mh, sh ) + self._logpdfm2(m2, beta, ml, sl, mh, sh )
        
        if self.normalization=='integral':
            logNorm = -np.log(self._get_normalization(lambdaBBHmass))
        elif self.normalization=='pivot':
            logNorm = alpha*np.log(30)-beta*np.log(30)-2*self._logf_smooth(30, ml=ml, sl=sl, mh=mh, sh=sh)-2*np.log(30)
        
        return logpdfMass+logNorm
        
       
    def _logf_smooth(self, m, ml=5, sl=0.1, mh=45, sh=0.1):
                
        return np.log(ss.norm().cdf((np.log(m)-np.log(ml))/sl))+np.log((1-ss.norm().cdf((np.log(m)-np.log(mh))/sh)))
       
    
    def _get_normalization(self, lambdaBBHmass):
        '''Normalization of p(m1, m2 | Lambda ). Warning: works well only when sl and sh are small '''
        alpha, beta, ml, sl, mh, sh = lambdaBBHmass
        
        if (beta!=-1) & (alpha!=1) : 
            return (( mh**(-alpha+beta+2)- ml**(-alpha+beta+2) )/(-alpha+beta+2) - ml**(beta+1) *(mh**(-alpha+1)-ml**(-alpha+1))/(-alpha+1) )/(beta+1)
        else:
            raise ValueError 
    
    
    def sample(self, nSamples, lambdaBBHmass):
        alpha, beta, ml, sl, mh, sh = lambdaBBHmass
        mMin = 3
        mMax = 100
        
        pm1 = lambda x: np.exp(self._logpdfm1(x, alpha, ml, sl, mh, sh ))
        pm2 = lambda x: np.exp(self._logpdfm2(x, beta, ml, sl, mh, sh ))
        
        m1 = self._sample_pdf(nSamples, pm1, mMin, mMax)
        m2 = self._sample_vector_upper(pm2, mMin, m1)
        
            
        return m1, m2

    


##############################################################################
# Truncated power law


class TruncPowerLawMass(BBHDistFunction):
    
    '''
    Mass distribution  - Truncated Power Law
    '''

    def __init__(self):
        
        BBHDistFunction.__init__(self)
        
        self.params = ['alpha', 'beta', 'ml',  'mh', ]
        
        self.baseValues = {
                           
                           'alpha':0.75,
                           'beta':0.0, 
                           'ml':4.0, 
                           'mh':78.5,
                           }
        
        self.names = {
                           'alpha':r'$\alpha$',
                           'beta':r'$\beta$', 
                           'ml':r'$M_l$', 
                           'mh':r'$M_h$',}
         
        self.n_params = len(self.params)
    
    
    def _logpdfm1(self, m, alpha, ml, mh):
        '''
        Marginal distribution p(m1)
        '''
       
        
        where_nan = np.isnan(m)
        result = np.empty_like(m)
        

        result[where_nan]=np.NINF
        
        where_compute = (ml < m) & (m < mh )
        result[~where_compute] = np.NINF
        
        m = m[where_compute]
        result[where_compute] = np.log(m)*(-alpha)
        
        return result
    
    
    def _logpdfm2(self, m, beta, ml):
        '''
        Conditional distribution p(m2 | m1)
        '''
        where_nan = np.isnan(m)
        result = np.empty_like(m)
        

        result[where_nan]=np.NINF
        
        where_compute = (ml < m)
        result[~where_compute] = np.NINF
        
        m = m[where_compute]
        result[where_compute] = np.log(m)*(beta) 
        
        return result
    
    
    def logpdf(self, theta, lambdaBBHmass):
        
        '''p(m1, m2 | Lambda ), normalized to one'''
        
        m1, m2 = theta
        alpha, beta, ml, mh = lambdaBBHmass
        
        where_compute = (m2 < m1) & (ml < m2) & (m1 < mh )
     
        return np.where( where_compute,   self._logpdfm1(m1, alpha, ml, mh) + self._logpdfm2(m2, beta, ml) +self._logC(m1, beta, ml) -  self._logNorm( alpha, ml, mh) ,  np.NINF)
        
    
    
    def _logC(self, m, beta, ml):
        '''
        Gives inverse log integral of  p(m1, m2) dm2 (i.e. log C(m1) in the LVC notation )
        Used if we want to impose that the  distribution _logpdfm1 corresponds to the marginal distribution p(m1)
        '''
        if beta>-1:
            return np.log1p(beta)-utils.logdiffexp((1+beta)*np.log(m), (1+beta)*np.log(ml)) # -beta*np.log(m)
        elif beta<-1:
            return +np.log(-1-beta)-utils.logdiffexp( (1+beta)*np.log(ml), (1+beta)*np.log(m)) #-beta*np.log(m)
        raise ValueError # 1 / m / np.log(m / ml)


    def _logNorm(self, alpha, ml, mh):
        '''
        Gives log integral of  p(m1, m2) dm1 dm2 (i.e. total normalization of mass function )

        '''
        if (alpha < 1) & (alpha!=0):
            return -np.log1p(-alpha)+utils.logdiffexp( (1-alpha)*np.log(mh), (1-alpha)*np.log(ml) ) #(1 - alpha) / (mh ** (1 - alpha) - ml ** (1 - alpha))

        elif (alpha > 1) :
            return -np.log(alpha-1)+utils.logdiffexp(  (1-alpha)*np.log(ml), (1-alpha)*np.log(mh) )
        raise ValueError
       
    
    def sample(self, nSamples, lambdaBBHmass):
        alpha, beta, ml, mh = lambdaBBHmass

        
        pm1 = lambda x: np.exp(self._logpdfm1(x, alpha, ml, mh ))
        pm2 = lambda x: np.exp(self._logpdfm2(x, beta, ml ))
        
        m1 = self._sample_pdf(nSamples, pm1, ml, mh)
        #m2 = self._sample_pdf(nSamples, pm2, mMin, mMax)
        m2 = self._sample_vector_upper(pm2, ml, m1)
        assert(m2<=m1).all() 
        assert(m2>=ml).all() 
        assert(m1<=mh).all() 
            
        return m1, m2



##############################################################################
# Broken power law


class BrokenPowerLawMass(BBHDistFunction):
    
    '''
    Mass distribution  - Truncated Power Law
    '''

    def __init__(self):
        
        BBHDistFunction.__init__(self)
        
        self.params = ['alpha1', 'alpha2', 'beta', 'deltam', 'ml',  'mh', 'b' ]
        
        self.baseValues = {
                           'alpha1':1.6,
                           'alpha2': 5.6 , 
                           'beta': 1.4,
                           'deltam':4.8,
                           'ml':4,
                           'mh':87,
                           'b': 0.43,
                           }
        
        self.names = { 'alpha1': r'$\alpha_1$',
                           'alpha2':  r'$\alpha_2$' , 
                           'beta':  r'$\beta_q$',
                           'deltam': r'$\delta_{\rm m}$',
                           'ml': r'$m_{\rm min}$',
                           'mh':r'$m_{\rm max}$',
                           'b': r'$b$',
                           
                           }
         
        self.n_params = len(self.params)
        
        print('Broken power law mass function base values: %s' %self.baseValues)
    
    
    def _get_Mbreak(self, mMin, mMax, b):
        return  mMin + b*(mMax - mMin)
    
    
    def _logS(self, m, deltam, ml,):
        maskL = m <= ml #- eps
        maskU = m >= (ml + deltam) #+ eps
        s = np.empty_like(m)
        s[maskL] = np.NINF
        s[maskU] = 0
        maskM = ~(maskL | maskU)
        s[maskM] = -np.logaddexp( 0, (deltam/(m[maskM]-ml) + deltam/(m[maskM]-ml - deltam) ) ) #1/(np.exp(deltam/(m[maskM]-ml) + deltam/(m[maskM]-ml - deltam))+1)
        return s
    
    
    def _logpdfm1(self, m,  alpha1, alpha2, deltam, ml, mh, b):
        '''
        Marginal distribution p(m1), not normalised
        '''

        mBreak = self._get_Mbreak( ml, mh, b)
        
        where_nan = np.isnan(m)
        result = np.empty_like(m)
        
        result[where_nan]=np.NINF
        
        where_compute = (m <= mh) & (m >= ml) & (~where_nan)
        result[~where_compute] = np.NINF
        
        m = m[where_compute]
        result[where_compute] = np.where(m < mBreak, np.log(m)*(-alpha1)+self._logS(m, deltam, ml), np.log(mBreak)*(-alpha1+alpha2)+np.log(m)*(-alpha2)+self._logS(m, deltam, ml) )
        
        return result
        
    
    
    def _logpdfm2(self, m2, beta, deltam, ml):
        '''
        Conditional distribution p(m2 | m1)
        '''
        where_nan = np.isnan(m2)
        result = np.empty_like(m2)

        result[where_nan]=np.NINF
        
        where_compute = (ml<= m2) & (~where_nan)
        result[~where_compute] = np.NINF
        
        m2 = m2[where_compute]
        result[where_compute] = np.log(m2)*(beta)+self._logS(m2, deltam, ml)
        return result
        
    
    
    def logpdf(self, theta, lambdaBBHmass, **kwargs):
        
        '''p(m1, m2 | Lambda ), normalized to one'''
        
        m1, m2 = theta
        alpha1, alpha2, beta, deltam, ml, mh, b = lambdaBBHmass
        
        where_nan = np.isnan(m1)
        assert (where_nan==np.isnan(m2)).all()
        result = np.empty_like(m1)

        result[where_nan]=np.NINF
        
        where_compute = (m2 < m1) & (ml< m2) & (m1 < mh ) & (~where_nan)
        result[~where_compute] = np.NINF
        
        m1 = m1[where_compute]
        m2 = m2[where_compute]
        
        result[where_compute] = self._logpdfm1(m1,  alpha1, alpha2, deltam, ml, mh, b ) + self._logpdfm2(m2, beta, deltam, ml) + self._logC(m1, beta, deltam,  ml, **kwargs)-  self._logNorm( alpha1, alpha2, deltam, ml, mh, b,)
        return result
        
        
        
    
    
    def _logC(self, m, beta, deltam, ml, res = 200, exact_th=0.):
        '''
        Gives inverse log integral of  p(m1, m2) dm2 (i.e. log C(m1) in the LVC notation )
        '''
        xlow=np.linspace(ml, ml+deltam+deltam/10, 200)
        xup=np.linspace(ml+deltam+deltam/10+1e-01, m[~np.isnan(m)].max(), res)
        xx=np.sort(np.concatenate([xlow,xup], ))
  
        p2 = np.exp(self._logpdfm2( xx , beta, deltam, ml))
        cdf = cumtrapz(p2, xx)
        
        where_compute = ~np.isnan(m)
        where_exact = m <exact_th*ml
        
        where_approx = (~where_exact) & (where_compute)
        
        
        result = np.empty_like(m)
        
        result[~where_compute]=np.NINF
        result[where_exact]=self._logCexact(m[where_exact], beta, deltam, ml,) #np.NINF
        
        result[where_approx] = -np.log( np.interp(m[where_approx], xx[1:], cdf) )
        
        return result
    
    
    def _logCexact(self, m, beta, deltam, ml, res=1000):
        result=[]

        for mup in m:

            xx = np.linspace(ml, mup, res)
            p2 = np.exp(self._logpdfm2( xx , beta, deltam, ml))
            result.append(-np.log(np.trapz(p2,xx)) )

    
        return np.array(result)
        


    def _logNorm(self, alpha1, alpha2, deltam, ml, mh, b , res=200):
        '''
        Gives log integral of  p(m1, m2) dm1 dm2 (i.e. total normalization of mass function )

        '''
        
        
        mbr = self._get_Mbreak( ml, mh, b)
        

        ms1 = np.linspace(1., ml+deltam+deltam/10, 200)
        ms2 = np.linspace( ml+deltam+deltam/10+1e-01, mbr-mbr/10, int(res/2) )
        ms3= np.linspace( mbr-mbr/10+1e-01, mbr+mbr/10, 50 )
        ms3 = np.linspace(mbr+mbr/10+1e-01, mh+mh/2, int(res/2) )
        
        ms=np.sort(np.concatenate([ms1,ms2, ms3], ))
        
        p1 = np.exp(self._logpdfm1( ms ,alpha1, alpha2, deltam, ml, mh, b ))
        return np.log(np.trapz(p1,ms))
        
    
    
    def _logNorm1(self, alpha1, alpha2, deltam, ml, mh, b ):
        '''
        Gives log integral of  p(m1, m2) dm1 dm2 (i.e. total normalization of mass function )

        '''
        mbr = self._get_Mbreak( ml, mh, b)
        x3 = +np.log( mbr**(1-alpha1)*(alpha2-alpha1)-ml**(1-alpha1)*(1-alpha2) +mh**(1-alpha2)*mbr**(alpha2-alpha1)*(1-alpha1) )
        if np.isnan(x3):
            raise ValueError
        
        if (alpha1 < 1) & (alpha2<1) & (alpha1 != 0) & (alpha2!= 0) :
            x1 = -np.log1p(-alpha1)
            x2 = -np.log1p(-alpha2)

        elif (alpha1 > 1) & (alpha2<1) :
            x1 = -np.log(alpha1-1)
            x2 = -np.log1p(-alpha2)

        elif  (alpha1 < 1) & (alpha2>1) :   
            x1 = -np.log1p(-alpha1)
            x2 = -np.log(alpha2-1)
        elif (alpha1 > 1) & (alpha2>1):
            x1 = -np.log(alpha1-1)
            x2 = -np.log(alpha2-1)
        else:
            raise ValueError
        
        return x1+x2+x3
        
    
    
    def sample(self, nSamples, lambdaBBHmass, mMin=5, mMax=100):
        alpha1, alpha2, beta, deltam, ml, mh, b = lambdaBBHmass
        
        
        pm1 = lambda x: np.exp(self._logpdfm1(x, alpha1, alpha2, deltam, ml, mh, b ))
        pm2 = lambda x: np.exp(self._logpdfm2(x,  beta, deltam, ml ))
        
        m1 = self._sample_pdf(nSamples, pm1, mMin, mMax)
        m2 = self._sample_vector_upper(pm2, mMin, m1)
        assert(m2<=m1).all() 
        assert(m2>=ml).all() 
        assert(m1<=mh).all() 
            
        return m1, m2



##############################################################################
# Dummy class; for testing


class AstroGaussMass(BBHDistFunction):
    
    '''
    Mass distribution  - Gaussian in the first mass flat in the second
    '''
    
    def __init__(self, ):
        
        BBHDistFunction.__init__(self)
        
        self.params = ['meanMass', 'sigmaMass']
        
        self.baseValues = {
                           
                           'meanMass':20,
                           'sigmaMass':10, 
                           }
        
        self.names = {
                           'meanMass':r'$\mu_{\rm mass}$',
                           'sigmaMass':r'$\sigma_{\rm mass}$', 
                           }
         
        self.n_params = len(self.params)
    
        
    
    
    def logpdf(self, theta, lambdaBBHmass):
        
        '''p(m1, m2 | Lambda ), normalized to one'''
        
        m1, m2 = theta
        meanMass, sigmaMass = lambdaBBHmass
        
        condition = (m2<m1) & (m2>5)
        if not condition:
            return np.NINF
    
        logpdfMass = (-np.log(sigmaMass)-(m1-meanMass)**2/(2*sigmaMass**2)) 
        
        return logpdfMass
    
    
