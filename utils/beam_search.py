import numpy as np
from chainer import cuda
from chainer import Variable
import chainer.functions as F


def beam_search(dec,state,y,data,beam_width,mydict_inv):  
    beam_width=beam_width
    xp=cuda.cupy
    batchsize=data.shape[0]
    vocab_size=len(mydict_inv)
    topk=20
    route = np.zeros((batchsize,beam_width,50)).astype(np.int32)
    
    for j in range(50):
        if j == 0:
            y = Variable(xp.array(np.argmax(y.data.get(), axis=1)).astype(xp.int32))
            state,y = dec(y, state, train=False)
            h=state['h1'].data
            c=state['c1'].data
            h=xp.tile(h.reshape(batchsize,1,-1), (1,beam_width,1))
            c=xp.tile(c.reshape(batchsize,1,-1), (1,beam_width,1))
            ptr=F.log_softmax(y).data.get()
            pred_total_city = np.argsort(ptr)[:,::-1][:,:beam_width]
            pred_total_score = np.sort(ptr)[:,::-1][:,:beam_width]
            route[:,:,j] = pred_total_city
            pred_total_city=pred_total_city.reshape(batchsize,beam_width,1)
        else:
            pred_next_score=np.zeros((batchsize,beam_width,topk))
            pred_next_city=np.zeros((batchsize,beam_width,topk)).astype(np.int32)
            score2idx=np.zeros((batchsize,beam_width,topk)).astype(np.int32)
            for b in range(beam_width):
                state={'c1':Variable(c[:,b,:]), 'h1':Variable(h[:,b,:])}
                cur_city = xp.array([pred_total_city[i,b,j-1] for i in range(batchsize)]).astype(xp.int32)
                state,y = dec(cur_city,state, train=False)
                h[:,b,:]=state['h1'].data
                c[:,b,:]=state['c1'].data
                ptr=F.log_softmax(y).data.get()
                pred_next_score[:,b,:]=np.sort(ptr, axis=1)[:,::-1][:,:topk]
                pred_next_city[:,b,:]=np.argsort(ptr, axis=1)[:,::-1][:,:topk]

            h=F.stack([h for i in range(topk)], axis=2).data
            c=F.stack([c for i in range(topk)], axis=2).data
            
            pred_total_city = np.tile(route[:,:,:j],(1,1,topk)).reshape(batchsize,beam_width,topk,j)
            pred_next_city = pred_next_city.reshape(batchsize,beam_width,topk,1)
            pred_total_city = np.concatenate((pred_total_city,pred_next_city),axis=3)

            pred_total_score = np.tile(pred_total_score.reshape(batchsize,beam_width,1),(1,1,topk)).reshape(batchsize,beam_width,topk,1)
            pred_next_score = pred_next_score.reshape(batchsize,beam_width,topk,1)
            pred_total_score += pred_next_score

            idx = pred_total_score.reshape(batchsize,beam_width * topk).argsort(axis=1)[:,::-1][:,:beam_width]

            pred_total_city = pred_total_city[:,idx//topk, np.mod(idx,topk), :][np.diag_indices(batchsize,ndim=2)].reshape(batchsize,beam_width,j+1)
            pred_total_score = pred_total_score[:,idx//topk, np.mod(idx,topk), :][np.diag_indices(batchsize,ndim=2)].reshape(batchsize,beam_width,1)
            h = h[:,idx//topk, np.mod(idx,topk), :][np.diag_indices(batchsize,ndim=2)].reshape(batchsize,beam_width,-1)
            c = c[:,idx//topk, np.mod(idx,topk), :][np.diag_indices(batchsize,ndim=2)].reshape(batchsize,beam_width,-1)

            route[:,:,:j+1] =pred_total_city
            if (pred_total_city[:,:,j] == 15).all():
                break


    return route[:,0,:j+1].tolist()
