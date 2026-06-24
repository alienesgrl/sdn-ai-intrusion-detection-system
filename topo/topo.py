from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.topo import Topo
from mininet.cli import CLI
from mininet.log import setLogLevel


class MyTopo(Topo):

    def build(self):

        # Switchler
        switches = {}
        for i in range(1, 7):
            switches[i] = self.addSwitch(f's{i}')

        # Hostlar
        hosts = {}
        for i in range(1, 22):
            hosts[i] = self.addHost(f'h{i}', ip=f'10.0.0.{i}/24')

        # Switch chain
        for i in range(1, 6):
            self.addLink(switches[i], switches[i+1])

        # Host bağlantıları
        host_links = [
            (1,1),(2,2),(3,3),(4,4),(5,5),(6,6),
            (7,1),(8,2),(9,3),(10,4),(11,5),(12,6),
            (13,1),(14,2),(15,3),(16,4),(17,5),(18,6),
            (19,1),(20,2),(21,3)
        ]

        for h, s in host_links:
            self.addLink(hosts[h], switches[s])


def run():

    topo = MyTopo()

    net = Mininet(
        topo=topo,
        controller=None,
        switch=OVSKernelSwitch,
        autoSetMacs=True
    )

    # Ryu controller (DIŞARIDAN)
    net.addController(
        RemoteController('c0', ip='127.0.0.1', port=6653)
    )

    net.start()

    print("\n*** Ağ hazır, CLI açılıyor...\n")

    CLI(net)

    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()