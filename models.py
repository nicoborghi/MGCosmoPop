#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 20 16:38:28 2021

@author: Michi
"""


####################
# This module contains modeling of the BBH mass function and rate
####################


from utils import *
import scipy.stats as ss


priorLimits  = ( (20, 140), (0.1, 10), (0, 10), (0, 10), (0, 10), (-3, 3), (5, 10), (1, 5), (20, 200), (1, 5) )


###########################################################################


def alpha( Lambda,  theta_sel, weights_sel, N_gen):
    return np.sum(dN_dm1zdm2zddL(theta_sel,  Lambda)/weights_sel)/N_gen


def logLik(Lambda, theta):
    '''
    Lambda:
     H0, Xi0, n, R0, alpha, beta, gamma, ml, sl, mh, sh
    
    Returns log likelihood for all data
    '''
    m1z, m2z, dL = theta
    lik = dN_dm1zdm2zddL(theta,  Lambda) # ( n_obs x n_samples )
    
    lik/=originalMassPrior(m1z, m2z)
    lik/=originalDistPrior(dL)
        
    return np.log(lik.mean(axis=-1)).sum(axis=-1)



def log_prior(Lambda):
    H0, Xi0, n, lambaRedshift,  alpha, beta, ml, sl, mh, sh  = Lambda
    allVariables = flatten(Lambda)
    condition=True
    for i, (limInf, limSup) in enumerate(priorLimits):
        condition &= limInf<allVariables[i]<limSup 
    if condition: 
        return 0.0
    else:
        return -np.inf


def log_posterior(Lambda, theta, theta_sel, weights_sel, N_gen):
    lp = log_prior(Lambda)
    Nobs=theta[0].shape[0]
    if not np.isfinite(lp):
        return -np.inf
    return lp + logLik(Lambda, theta)-Nobs*np.log(alpha(Lambda,  theta_sel, weights_sel, N_gen))


###########################################################################


def originalMassPrior(m1z, m2z):
    return np.ones(m1z.shape)

def originalDistPrior(dL):
    return np.ones(dL.shape)



def dN_dm1dm2dz(z, theta,  Lambda) :
    '''
    - theta is an array (m1z, m2z, dL, Tobs) where m1z, m2z, dL are arrays 
    of the GW posterior samples and Tobs the observation time
     
     Lambda = (H0, Xi0, n, lambaRedshift, lambdaBBH ) 
     lambdaBBH is the parameters of the BBH mass function 
    '''
    
    m1z, m2z, dL = theta
    H0, Xi0, n, lambaRedshift,  alpha, beta, ml, sl, mh, sh  = Lambda
    lambdaBBH=[ alpha, beta, ml, sl, mh, sh]
    
    m1, m2 = m1z/(1+z), m2z/(1+z)
    
    return redshiftPrior(z, lambaRedshift)*massPrior(m1, m2, lambdaBBH )



def dN_dm1zdm2zddL(theta,  Lambda) :
    
    m1z, m2z, dL = theta
    H0, Xi0, n, lambaRedshift,  alpha, beta, ml, sl, mh, sh  = Lambda
    
    z=z_from_dLGW_fast(dL, H0, Xi0, n=n)
    
    
    return  dN_dm1dm2dz(z, theta,  Lambda)/redshiftJacobian(z)/ddL_dz(z, H0, Xi0, n=n)


def redshiftJacobian(z):
    return (1+z)**2



def redshiftPrior(z, gamma):
    '''
    dV/dz *(1+z)^(gamma-1)  [Mpc^3]
    '''
    return 4*np.pi*j(z)*(1+z)**(gamma-1)*((clight/H0)**3)


def massPrior(m1, m2, lambdaBBH):
    '''
    lambdaBBH is the array of parameters of the BBH mass function 
    '''
    alpha, beta, gamma, ml, sl, mh, sh = lambdaBBH
    return (m1/30)**(-alpha)*(m2/30)**(beta)*f_smooth(m1, ml=ml, sl=sl, mh=mh, sh=sh)*f_smooth(m2, ml=ml, sl=sl, mh=mh, sh=sh)  
  
  
def f_smooth(m, ml=5, sl=0.1, mh=45, sh=0.1):
    return ss.norm().cdf((np.log(m)-np.log(ml))/sl)*(1-ss.norm().cdf((np.log(m)-np.log(mh))/sl))