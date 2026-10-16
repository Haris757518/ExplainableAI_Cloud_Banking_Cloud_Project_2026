"""CPU-feasible one-step forecasts; every feature precedes its target."""
import numpy as np
from common.research import PerformanceForecast

LAGS=12

def fit_models(values,train_end):
    y=np.asarray([np.nan if v is None else v for v in values],dtype=float)
    mean=float(np.nanmean(y[:train_end])); scale=max(float(np.nanstd(y[:train_end])),1e-8)
    x=[];targets=[]
    for i in range(LAGS,train_end):
        row=y[i-LAGS:i]
        if np.isfinite(row).all() and np.isfinite(y[i]):x.append(np.r_[1,(row-mean)/scale]);targets.append((y[i]-mean)/scale)
    if len(x)<20:return None
    x=np.asarray(x);targets=np.asarray(targets)
    penalty=np.eye(LAGS+1);penalty[0,0]=0
    coef=np.linalg.solve(x.T@x+penalty,x.T@targets)
    return {'coef':coef,'mean':mean,'scale':scale,'training_end_index':train_end}

def predict(values,index,model,method):
    if index<1:return None
    previous=values[index-1]
    if previous is None:return None
    if method=='persistence':return float(previous)
    if method=='seasonal_naive_24':return values[index-24] if index>=24 else None
    row=values[index-LAGS:index]
    if model is None or len(row)<LAGS or any(v is None for v in row):return None
    return float(model['mean']+model['scale']*(np.r_[1,(np.asarray(row)-model['mean'])/model['scale']]@model['coef']))

def forecast_evaluation(series):
    values=[p.value for p in series.observations];n=len(values);a,b=int(.6*n),int(.8*n)
    if a<36:return {'status':'insufficient_history'}
    model=fit_models(values,a)
    if model is None:return {'status':'insufficient_complete_training_windows'}
    methods=['persistence','seasonal_naive_24','ridge_ar12']
    validation={}
    for method in methods:
        errors=[abs(values[i]-p) for i in range(a,b) if values[i] is not None and (p:=predict(values,i,model,method)) is not None]
        validation[method]=float(np.mean(errors)) if errors else float('inf')
    selected=min(validation,key=validation.get)
    residuals=[abs(values[i]-p) for i in range(a,b) if values[i] is not None and (p:=predict(values,i,model,selected)) is not None]
    if not residuals:return {'status':'insufficient_validation'}
    radius=float(np.quantile(residuals,.9,method='higher'))
    limit=float(np.nanquantile([np.nan if v is None else v for v in values[:a]],.95))
    scores={}
    for method in methods:
        pairs=[(values[i],p) for i in range(b,n) if values[i] is not None and (p:=predict(values,i,model,method)) is not None]
        delta=np.asarray([v-p for v,p in pairs])
        scores[method]={'mae':float(np.mean(abs(delta))) if len(delta) else None,'rmse':float(np.sqrt(np.mean(delta**2))) if len(delta) else None,'targets':len(pairs)}
    pairs=[(values[i],p) for i in range(b,n) if values[i] is not None and (p:=predict(values,i,model,selected)) is not None]
    coverage=sum(abs(v-p)<=radius for v,p in pairs)/len(pairs) if pairs else None
    return {'status':'evaluated','selected_on_validation':selected,'split':{'train':[0,a],'validation':[a,b],'test':[b,n]},'methods':scores,'validation_mae':validation,'interval_radius':radius,'interval_coverage':coverage,'interval_nominal':.9,'threshold_reference':limit,'threshold_warning':{'true_positive':sum(v>limit and p>limit for v,p in pairs),'false_positive':sum(v<=limit and p>limit for v,p in pairs),'false_negative':sum(v>limit and p<=limit for v,p in pairs)},'warning_definition':'Exceeds training-only 95th percentile; not a verified incident label.','interval_limit':'Validation absolute residual quantile; dependent series violate exchangeability, so nominal coverage is not guaranteed.'}

def forecast_next(series):
    points=series.observations;values=[p.value for p in points];n=len(values)
    base=dict(series_id=series.id,model='validation-selected persistence/seasonal-naive/ridge-AR12',reliability='Insufficient history; no forecast emitted.')
    if n<60:return PerformanceForecast(status='insufficient_history',**base)
    a,b=int(.6*n),int(.8*n);model=fit_models(values,a)
    if model is None:return PerformanceForecast(status='insufficient_complete_history',**base)
    candidates={}
    for method in ['persistence','seasonal_naive_24','ridge_ar12']:
        residual=[abs(values[i]-p) for i in range(a,b) if values[i] is not None and (p:=predict(values,i,model,method)) is not None]
        if residual:candidates[method]=residual
    if not candidates:return PerformanceForecast(status='insufficient_validation',**base)
    method=min(candidates,key=lambda m:np.mean(candidates[m]));value=predict(values,n,model,method)
    if value is None:return PerformanceForecast(status='latest_history_missing',**base)
    radius=float(np.quantile(candidates[method],.9,method='higher'))
    intervals=[b.timestamp-a.timestamp for a,b in zip(points,points[1:])]
    regular=bool(series.period_seconds) and all(abs(d-series.period_seconds)<=max(1e-6,.01*series.period_seconds) for d in intervals)
    warning=float(np.nanquantile([np.nan if v is None else v for v in values[:a]],.95))
    return PerformanceForecast(status='forecast',model=method,series_id=series.id,timestamp=points[-1].timestamp+series.period_seconds if regular else None,value=value,lower=value-radius,upper=value+radius,threshold_reference=warning,expected_threshold_exceedance=value>warning,interval_interpretation='90% validation absolute-residual interval; empirical time-series coverage must be evaluated.',reliability='One observed-record ahead, using this prefix only. '+('Regular source cadence.' if regular else 'Irregular source cadence: calendar prediction time is unknown; no fixed-time-horizon claim.')+' Warning threshold is the training-only 95th percentile, not an SLO or verified incident.')
