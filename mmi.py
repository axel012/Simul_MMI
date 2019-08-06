import random
import math
import time

seed = time.time()
random.seed(seed)
print("Using seed %d"%(seed))
debug = False

class Event:
    "Event class"
    def __init__(self,name,rate,handler):
        self.name = name
        self.rate = rate
        self.handler = handler
        self.nextOcurrenceTime = 0
        self.disabled = False
    def disable(self):
        self.disabled = True
    def callHandler(self,param):
        self.handler(self,param)
    def enable(self):
        self.disabled = False
    def reset(self):
        self.disable()
        self.nextOcurrenceTime = 0
    def getNextOcurrenceTime(self,reloj):
        self.enable()
        self.nextOcurrenceTime = (-self.rate * math.log(random.random())) + reloj
        return self.nextOcurrenceTime

class Arribo(Event):
    "Arribal event"
    def __init__(self,name,rate,handler):
        Event.__init__(self,name,rate,handler)
    def callHandler(self,param):
        self.handler(param)

class Partida(Event):
    "Leave event"
    def __init__(self,name,rate,handler,serverID):
        Event.__init__(self,name,rate,handler)
        self.serverID = serverID
    def callHandler(self,param):
        self.handler(param,self.serverID)



class ServerStats:
    "Contains server's statics counters"
    def __init__(self):
         #----CONTADORES ESTADISTICOS-------
        #qt: acumulado area Q(t)
        #cccd: cantidad clientes completaron su demora
        #sd: acumulado demora promedio
        #ts: acumulado tiempo de servicio
        #bt: acumulado utilizacion del servidor
        self.qt = 0
        self.cccd = 0
        self.sd = 0
        self.ts = 0
        self.bt = 0
        self.cola = []
        self.servidorOcupado = False
        self.longCola = 0
        self.tServidorOcupado = 0
    def __str__(self):
        return "{qt:%f, cccd:%d, sd:%f , ts: %f , bt: %f}"%(self.qt,self.cccd,self.sd,self.ts,self.bt)

        
class MMI:
    def __init__(self,nServidores):
        self._events = {}
        self.nServidores = nServidores
    def initialization(self,eventos):
        self._servers = []
        for i in range(self.nServidores):
            self._servers.append(ServerStats())
        self.reloj = 0
        self.relojA = self.reloj #estado anterior del reloj
        #reseteamos los eventos a su estado inicial (nextOcurrenceTime = 0, disabled = True)
        for eventName in self._events:
            event = self._events[eventName]
            event.reset()
        #Eventos que deben inicializarse su proximaOcurrencia - en este caso arribo, pero
        #el codigo permite manejar varios eventos que pongamos como iniciales
        for e in eventos:
            e.getNextOcurrenceTime(self.reloj)       
    def registerEvent(self,event):
        self._events[event.name] = event
        return event
    def generateNextEvent(self,name):
        return (self._events[name]).getNextOcurrenceTime(self.reloj) 
    def getNextEvent(self):
        minE = 999999
        nextEvent = None
        for eventName in self._events:
            event = self._events[eventName]
            if ( event.disabled ):
                continue
            if ( event.nextOcurrenceTime < minE ):
                minE = event.nextOcurrenceTime
                nextEvent = event
        return nextEvent
    def relojNextEvent(self):
        proximoEvento = self.getNextEvent()
        self.relojA = self.reloj
        self.reloj += proximoEvento.nextOcurrenceTime - self.relojA
        proximoEvento.callHandler(self)
    def findFreeServer(self):
        "return random free server or that with less queue"
        _min = 9999999
        server = None
        sid = 0
        frees = []
        for s in range(self.nServidores):
            current = self._servers[s]
            if(not current.servidorOcupado):
                frees.append((current,s))
            if(current.longCola < _min):
                _min = current.longCola
                server = current
                sid = s
        if(len(frees) == 0):
            return (server,sid)
        else:#pick random free server, this prevents always chosing server 0
            return random.choice(frees)
    def getServerById(self,sid):
        return self._servers[sid]
    def reporte(self):
        ret = []
        for i in range(self.nServidores):
            server = self._servers[i]
            demoraPromedio =  (server.sd/float(server.cccd)) * 60 if server.cccd != 0 else 0
            numeroPromedioClientesCola = server.qt/float(self.reloj)
            if(server.servidorOcupado):
                server.bt += (self.reloj - server.tServidorOcupado)
            utilizacionServidor = (server.bt/float(self.reloj))*100
            tiempoServicioPromedio =  ((server.ts/float(server.cccd))*60) if (server.cccd != 0) else 0
            if(debug):
                print("\tDemoraPromedio: %fmin\n\
            NumeroPromedioClientesCola: %f clientes\n\
            UtilizacionServidor: %f%%\r\n\
            TiempoServicioPromedio: %f" \
            %(demoraPromedio,numeroPromedioClientesCola,utilizacionServidor,tiempoServicioPromedio))
            ret.append((demoraPromedio,numeroPromedioClientesCola,utilizacionServidor,tiempoServicioPromedio))
        return ret
   

#funcion manejadora del evento arribo
def farribo(self):  

    (server,sid) = self.findFreeServer()
    self.generateNextEvent("arribo")
    if(server.servidorOcupado == False):
        server.servidorOcupado = True
        server.tServidorOcupado = self.reloj
        #actualizar estadisticos
        server.cccd += 1
        server.ts += (self.generateNextEvent("partida%d"%(sid)) - self.reloj) 
        #partida del cliente que arribo a la cola vacia
    else:
        colaLen = server.longCola
        server.qt += (self.reloj - self.relojA) * colaLen
        server.cola.append(self.reloj)
        server.longCola += 1

#funcion manejadora del evento partida
def fpartida(self,serverID):
    server = self.getServerById(serverID)
    if(server.longCola == 0):
            #si no hay clientes no puede existir una partida como proximo evento
        (self._events["partida%d"%(serverID)]).disable() 
        server.servidorOcupado = False
        server.bt += (self.reloj - server.tServidorOcupado)
    else:
        #calculamos la partida del cliente que sale de la cola
        server.ts += (self.generateNextEvent("partida%d"%(serverID)) - self.reloj) 
        colaLen = server.longCola
        server.qt += (self.reloj - self.relojA) * colaLen
        t = server.cola.pop(0) #tiempo de llegada a la cola del cliente que parte
        server.longCola -= 1
        server.sd += (self.reloj - t)
        server.cccd += 1


#-------main program------------#
nServidores = int(input("Ingrese número de servidores: "))
mmi = MMI(nServidores)
ta = int(input("Ingrese tasa de arribo: "))
ts = int(input("Ingrese tasa de servicio: "))

tasaArribo = 1/float(ta)
tasaServicio = 1/float(ts)

arribo = mmi.registerEvent(Arribo("arribo",tasaArribo,farribo))
sumatoriaReplicas = []
for i in range(nServidores):
    mmi.registerEvent(Partida("partida%d"%(i),tasaServicio,fpartida,i))
    sumatoriaReplicas.append((0,0,0,0))

numeroReplicas = int(input("Ingrese numero de replicas: "))
for i in range(0,numeroReplicas):
    mmi.initialization([arribo])
    while(mmi.reloj < 8):
        mmi.relojNextEvent()
    report = mmi.reporte()
    for j in range(len(report)):
        reportTuple = report[j]
        sumatoriaReplicas[j] = tuple(map(sum,zip(sumatoriaReplicas[j],reportTuple)))

#divido la sumatoria por el numero de replicas
resultado = []
for t in range(len(sumatoriaReplicas)):
    prom = sumatoriaReplicas[t]
    resultado.append(tuple([x/float(numeroReplicas) for x in prom]))

#para cada servidor muestro los estadisticos recolectados
for i in range(len(resultado)):
    print("Servidor %d"%(i))
    print("\tDemoraPromedio: %f min\n\
        NumeroPromedioClientesCola: %f clientes\n\
        UtilizacionServidor: %f%%\r\n\
        TiempoServicioPromedio: %f min" \
        %resultado[i])
