# Formato del log filterlog de pfSense (verificado)

Investigación realizada con Perplexity, contra fuentes primarias:

- Gramática BNF oficial: https://docs.netgate.com/pfsense/en/latest/monitoring/logs/raw-filter-format.html
- Código fuente `parse_firewall_log_line()`: https://github.com/pfsense/pfsense/blob/master/src/etc/inc/syslog.inc
- Script oficial `filterparser.php`: https://github.com/pfsense/pfsense/blob/master/src/usr/local/bin/filterparser.php

## Orden de campos confirmado (IPv4)

```
rulenum,subrulenum,anchor,tracker,realint,reason,action,direction,version,
tos,ecn,ttl,id,offset,flags,protoid,prototext,
length,srcip,dstip,
[TCP/UDP] srcport,dstport,datalen
[solo TCP] tcpflags,seq,ack,window,urg,options
```

En IPv6 el orden de version-specific data cambia: class,flow-label,hop-limit,
protocol-text,protocol-id -- el texto de protocolo va ANTES del ID numérico,
al revés que en IPv4.

## Ejemplo real citado por la documentación oficial

```
Jan 21 18:01:01 1.2.3.4 filterlog[90111]: 8,,,1000000100,en1,match,block,in,4,0x20,,242,27266,0,none,6,tcp,40,1.2.3.4,5.6.7.8,55341,8080,0,S,
```

Este formato es el que implementa `scripts/generate_fake_logs.py` para generar
datos sintéticos de prueba fieles al formato real, sin depender de un pfSense
disponible.
